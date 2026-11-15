"""Build the deployable archive website into site/.

Gathers, from the archive (read-only):
- every recording's chunked transcript -> a web copy of its audio + segments
- the event list (reviewed copy if present, else the machine draft)
- every finished story chapter -> copied in, images compressed for the web
and writes site/data.js for site-src/index.html.

The originals in media/ are never modified. site/ can be deleted and rebuilt at any time.

Usage:
    python tools/build_site.py
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe_chunked import FFMPEG  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DERIVED = ROOT / "archive" / "derived"

PEOPLE = [
    {"id": "dad", "name_en": "Dad", "name_hi": "पापा", "status": "recorded"},
    {"id": "mum", "name_en": "Mum", "name_hi": "मम्मी", "status": "coming"},
    {"id": "dadi", "name_en": "Dadi", "name_hi": "दादी", "status": "coming"},
]
NOTE = ("Draft. Transcripts, translations and dates are AI drafts that the family has not yet checked. "
        "Words with a dotted underline were unclear. Story images are illustrations, not photographs. "
        "Map locations are approximate.")


def run(*args):
    subprocess.run([FFMPEG, "-v", "error", "-y", *map(str, args)], check=True)


def duration(f: pathlib.Path) -> float:
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)",
                  subprocess.run([FFMPEG, "-i", str(f)], capture_output=True, text=True).stderr)
    return round(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), 2)


def newer(src: pathlib.Path, dst: pathlib.Path) -> bool:
    return not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime


def build_tv(data: dict) -> None:
    """site-tv/: the TV version (old-browser page, served at /tv/stories/?key=...).

    Same moments and captions; each story plays as its finished landscape video from exports/
    (made by tools/render_video.py), because the TV's old browser can't run the animated page.
    """
    tv = ROOT / "site-tv"
    (tv / "chapters").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "site-src" / "tv.html", tv / "index.html")
    for sub in ("media", "photos"):
        if (SITE / sub).exists():
            shutil.copytree(SITE / sub, tv / sub, dirs_exist_ok=True)
    chapters = []
    for c in data["chapters"]:
        c = dict(c)
        mp4 = ROOT / "exports" / f"{c['title_en'].title()} - landscape.mp4"
        if mp4.exists():
            dst = tv / "chapters" / f"{c['id']}.mp4"
            if newer(mp4, dst):
                shutil.copy2(mp4, dst)
            c["video"] = f"chapters/{c['id']}.mp4"
        else:
            print(f"  TV: no video for chapter {c['id']} (render it with tools/render_video.py)")
        chapters.append(c)
    tv_data = {**data, "chapters": chapters}
    (tv / "data.js").write_text("window.ARCHIVE = " + json.dumps(tv_data, ensure_ascii=False) + ";\n", encoding="utf-8")
    size = sum(f.stat().st_size for f in tv.rglob("*") if f.is_file()) / 1e6
    print(f"site-tv/: {sum(1 for c in chapters if c.get('video'))} story videos, {size:.1f} MB")


def main() -> None:
    (SITE / "media").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "site-src" / "index.html", SITE / "index.html")

    # ---- recordings
    originals = {p.name: p for p in (ROOT / "media").rglob("*.m4a")}
    recordings = []
    for n, f in enumerate(sorted(DERIVED.glob("REC-*/transcript.gemini-pro-latest.chunked.json")), 1):
        rec_id = f.parent.name
        tr = json.loads(f.read_text(encoding="utf-8"))
        src = originals[tr["source"]["file"]]
        web = SITE / "media" / f"{rec_id}.m4a"
        if newer(src, web):  # mono speech copy, small and quick to seek
            run("-i", src, "-ac", "1", "-c:a", "aac", "-b:a", "80k", "-movflags", "+faststart", web)
        recordings.append({
            "id": rec_id, "title": f"Interview {n}", "person": "Dad", "file": f"media/{rec_id}.m4a",
            "duration": duration(web),
            "segments": [{k: s[k] for k in ("start", "end", "speaker", "text_hi", "text_en")} for s in tr["segments"]],
        })

    # ---- events (a reviewed copy, if it exists, always wins over the machine draft)
    ev_file = ROOT / "archive" / "reviewed" / "events.json"
    if not ev_file.exists():
        ev_file = DERIVED / "events.json"
    events = json.loads(ev_file.read_text(encoding="utf-8"))["events"] if ev_file.exists() else []
    rec_ids = {r["id"] for r in recordings}
    events = [e for e in events if all(s["recording"] in rec_ids for s in e.get("sources", []))]

    # ---- chapters
    chapters = []
    for cfg_file in sorted((ROOT / "stories").glob("*/story.config.json")):
        folder = cfg_file.parent
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        story = json.loads(re.search(r"\{.*\}", (folder / "story.js").read_text(encoding="utf-8"), re.S)[0])
        out = SITE / "chapters" / folder.name
        (out / "images").mkdir(parents=True, exist_ok=True)

        # images -> web JPEGs (the PNGs are ~2 MB each)
        renames = {}
        for png in (folder / "images").glob("*.png"):
            jpg = out / "images" / (png.stem + ".jpg")
            if newer(png, jpg):
                run("-i", png, "-q:v", "3", jpg)
            renames[f"images/{png.name}"] = f"images/{jpg.name}"
        js = (folder / "story.js").read_text(encoding="utf-8")
        for a, b in renames.items():
            js = js.replace(a, b)
        (out / "story.js").write_text(js, encoding="utf-8")
        for name in ("index.html", "audio.m4a", "music.m4a"):
            if (folder / name).exists():
                shutil.copy2(folder / name, out / name)
        if (folder / "photos").exists():
            shutil.copytree(folder / "photos", out / "photos", dirs_exist_ok=True)

        # which events does this chapter tell? (their source passage overlaps the chapter's)
        spans = [s["source"] for s in story["segments"] if s.get("source")]
        lo, hi = min(a for a, _ in spans), max(b for _, b in spans)
        covers = [e["id"] for e in events if any(
            s["recording"] == cfg["recording_id"] and s["start"] < hi and s["end"] > lo for s in e["sources"])]
        chapters.append({
            "id": folder.name, "url": f"chapters/{folder.name}/", "title_hi": cfg["title_hi"],
            "title_en": cfg["title_en"], "year": cfg.get("year"), "when": cfg.get("when", ""),
            "image": f"chapters/{folder.name}/" + renames.get(cfg.get("thumb", ""), "images/01-village.jpg"),
            "duration": duration(folder / "audio.m4a"), "event_ids": covers,
        })

    # ---- real photographs (prepared by tools/photos.py)
    photos = []
    pj = DERIVED / "photos" / "photos.json"
    if pj.exists():
        (SITE / "photos").mkdir(exist_ok=True)
        for p in json.loads(pj.read_text(encoding="utf-8")):
            shutil.copy2(pj.parent / f"{p['id']}.jpg", SITE / "photos" / f"{p['id']}.jpg")
            photos.append({"id": p["id"], "url": f"photos/{p['id']}.jpg", "caption": p["caption"], "date": p["date"],
                           "edits": p.get("_edits_text", ""), "events": p.get("events", []), "use": p.get("use", [])})
    for e in events:
        e["photos"] = [p["id"] for p in photos if e["id"] in p["events"]]

    data = {"people": PEOPLE, "recordings": recordings, "events": events, "chapters": chapters, "photos": photos,
            "note": NOTE}
    (SITE / "data.js").write_text("window.ARCHIVE = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    size = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file()) / 1e6
    print(f"site/: {len(recordings)} recordings, {len(events)} events, {len(chapters)} chapters, {size:.1f} MB")
    for c in chapters:
        print(f"  chapter {c['id']} covers events: {c['event_ids']}")
    build_tv(data)


if __name__ == "__main__":
    main()
