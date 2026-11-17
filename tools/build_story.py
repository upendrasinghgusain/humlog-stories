"""Build a story chapter from story.config.json.

- Cuts the chosen segments of Dad's speech from the original recording (read-only),
  snapping each cut to a real silence so words aren't clipped, and joins them with short pauses.
- Text cards become silent gaps with on-screen text.
- Writes audio.m4a and story.js (segments re-timed to the edited audio).

Corrections in the config apply only to the story's copy of the text; the machine transcript
file is left untouched.

Usage:
    python tools/build_story.py stories/<story-folder>
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe_chunked import FFMPEG  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RATE = 44100


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def silences(audio: pathlib.Path, a: float, b: float, noise: int = -30, d: float = 0.18) -> list[tuple[float, float]]:
    """Silent intervals (absolute seconds) in the original between a and b."""
    err = subprocess.run([FFMPEG, "-v", "info", "-ss", str(a), "-t", str(b - a), "-i", str(audio),
                          "-af", f"silencedetect=noise={noise}dB:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) + a for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) + a for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def mute_spans(cfg: dict, sil) -> list[tuple[float, float]]:
    """Short, separate bursts of sound next to an interviewer backchannel ("हम्म", "हाँ").

    Only bursts of <= 0.55 s that are bounded by silence are muted, so Dad's continuous speech
    is never touched. Backchannels spoken over Dad cannot be removed this way.
    """
    marks = json.loads((ROOT / cfg["interviewer_marks"]).read_text(encoding="utf-8")) if "interviewer_marks" in cfg else []
    # backchannels found by tools/refine_cuts.py ("auto") are hints too: their timing can be ~1 s off
    marks += [{"start": m[0], "end": m[1]} for m in cfg.get("mute", []) if m[2:] == ["auto"]]
    islands = [(sil[i][1], sil[i + 1][0]) for i in range(len(sil) - 1)]
    spans = []
    for m in marks:
        if m["end"] - m["start"] > 1.0:
            continue
        for a, b in islands:
            if b - a <= 0.55 and b > m["start"] - 0.8 and a < m["end"] + 0.8:
                spans.append((a - 0.05, b + 0.05))
    return spans


def snap_start(t: float, sil) -> float:
    """Move a cut-in point to just before speech resumes after the nearest silence."""
    near = [(abs(e - t), e) for s, e in sil if t - 1.6 <= e <= t + 1.0]
    return max(min(near)[1] - 0.12, 0) if near else t


def snap_end(t: float, sil) -> float:
    """Move a cut-out point to just after speech stops at the nearest silence."""
    near = [(abs(s - t), s) for s, e in sil if t - 1.0 <= s <= t + 1.6]
    return min(near)[1] + 0.2 if near else t


def main() -> None:
    folder = (ROOT / sys.argv[1]).resolve()
    cfg = json.loads((folder / "story.config.json").read_text(encoding="utf-8"))
    original = ROOT / cfg["audio_original"]
    tr = json.loads((ROOT / cfg["transcript"]).read_text(encoding="utf-8"))["segments"]
    fixes = cfg.get("corrections", {})
    gap = cfg.get("gap_seconds", 1.0)

    used = [i for item in cfg["edit"] for i in item.get("segs", [])]
    sil = silences(original, tr[min(used)]["start"] - 3, tr[max(used)]["end"] + 3)
    fine = silences(original, tr[min(used)]["start"] - 3, tr[max(used)]["end"] + 3, noise=-33, d=0.12)
    mutes = mute_spans(cfg, fine)
    # Explicit spans (absolute seconds, found by listening or a pitch check) for backchannels
    # that are not separated from Dad's words by silence.
    mutes += [tuple(m) for m in cfg.get("mute", []) if len(m) == 2]  # hand-checked spans only

    pieces, offsets, segs, t, card_no = [], [], [], 1.2, 0  # a short breath of room sound first
    songs = []  # (start, end) in the edited timeline, for ducking the music
    for item in cfg["edit"]:
        if "song" in item:
            # A few seconds of the narrator singing, from a separate recording. The caption shows only the
            # song's title, never its lyrics.
            sg = item["song"]
            dur = sg["end"] - sg["start"]
            segs.append({"start": round(t, 2), "end": round(t + dur, 2), "speaker": "SONG",
                         "text_hi": sg["hi"], "text_en": sg["en"], "key": f"song{len(songs)}"})
            pieces.append(("clip", sg["start"], sg["end"], ROOT / sg["file"]))
            offsets.append(t)
            songs.append((t, t + dur))
            t += dur + gap
            pieces.append(("silence", gap))
            offsets.append(t - gap)
            continue
        if "card" in item:
            segs.append({"start": round(t, 2), "end": round(t + item["seconds"], 2), "speaker": "CARD",
                         "text_hi": item["card"]["hi"], "text_en": item["card"]["en"], "key": f"card{card_no}"})
            pieces.append(("silence", item["seconds"]))
            offsets.append(t)
            t += item["seconds"]
            card_no += 1
            continue
        idx = item["segs"]
        # Explicit start/end (absolute seconds, set after listening checks) win over snapping.
        a = item.get("start") or snap_start(tr[idx[0]]["start"], sil)
        b = item.get("end") or snap_end(tr[idx[-1]]["end"], sil)
        pieces.append(("clip", a, b))
        offsets.append(t)
        for k, i in enumerate(idx):
            s = {**tr[i], **fixes.get(str(i), {})}
            st = a if k == 0 else s["start"]
            en = b if k == len(idx) - 1 else s["end"]
            segs.append({"start": round(t + st - a, 2), "end": round(t + en - a, 2), "speaker": "DAD",
                         "text_hi": s["text_hi"], "text_en": s["text_en"], "confidence": s["confidence"],
                         "key": i, "source": [round(st, 2), round(en, 2)]})
        t += (b - a) + gap
        pieces.append(("silence", gap))
        offsets.append(t - gap)

    # Assemble. Dead digital silence between passages sounds like drop-outs, so a continuous bed of
    # the room's own background sound runs underneath, and each passage fades in/out over it.
    total = t + 1.5
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        rt = cfg.get("room_tone", {"start": 176.6, "seconds": 0.9})
        subprocess.run([FFMPEG, "-v", "error", "-ss", str(rt["start"]), "-t", str(rt["seconds"]),
                        "-i", str(original), "-ac", "1", "-ar", str(RATE),
                        "-filter_complex", "[0]asplit[a][b];[b]areverse[r];[a][r]concat=n=2:v=0:a=1",
                        str(tmp / "tone.wav")], check=True)  # forward+reversed = seamless loop
        subprocess.run([FFMPEG, "-v", "error", "-stream_loop", "-1", "-i", str(tmp / "tone.wav"),
                        "-t", f"{total:.2f}", "-af",
                        # A noisy recording's snippet, looped, can sound like machinery: such chapters soften the
                        # bed ("room_tone_gain") and smooth it into a plain hush.
                        (f"highpass=f=150,lowpass=f=2200,volume={cfg['room_tone_gain']}," if "room_tone_gain" in cfg else "")
                        + "afade=t=in:d=1", str(tmp / "bed.wav")], check=True)

        inputs, chains, n = ["-i", str(tmp / "bed.wav")], [], 0
        for p, offset in zip(pieces, offsets):
            if p[0] != "clip":
                continue
            n += 1
            f = tmp / f"{n:03d}.wav"
            dur = p[2] - p[1]
            if len(p) > 3:  # a song clip from its own recording: level-matched to the speech, softer fades
                af = f"loudnorm=I=-21.5:TP=-3,afade=t=in:d=0.5,afade=t=out:st={dur - 1.2:.3f}:d=1.2"
                src = p[3]
            else:
                # Interviewer bursts are turned right down (not to zero) so the room never "drops out".
                mute = "".join(f"volume=enable='between(t,{max(x - p[1], 0):.2f},{y - p[1]:.2f})':volume=0.08,"
                               for x, y in mutes if y > p[1] and x < p[2])
                af = mute + f"afade=t=in:d=0.2,afade=t=out:st={dur - 0.35:.3f}:d=0.35"
                src = original
            subprocess.run([FFMPEG, "-v", "error", "-ss", f"{p[1]:.3f}", "-t", f"{dur:.3f}",
                            "-i", str(src), "-ac", "1", "-ar", str(RATE), "-af", af, str(f)], check=True)
            inputs += ["-i", str(f)]
            ms = int(offset * 1000)
            chains.append(f"[{n}]adelay={ms}|{ms}[v{n}]")
        mix = ";".join(chains) + ";[0]" + "".join(f"[v{k}]" for k in range(1, n + 1)) + \
            f"amix=inputs={n + 1}:normalize=0:duration=first,loudnorm=I=-18:TP=-2"
        subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", mix,
                        "-c:a", "aac", "-b:a", "128k", str(folder / "audio.m4a")], check=True)

        # Optional music bed: a separate, quiet track the page can switch off.
        if cfg.get("music"):
            # loops if the piece is shorter than the chapter; a chapter may ask for it louder ("music_lufs")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-stream_loop", "-1", "-i", str(folder / cfg["music"]),
                            "-t", f"{total:.2f}",
                            "-af", f"loudnorm=I={cfg.get('music_lufs', -33)}:TP=-9,afade=t=in:d=4,afade=t=out:st={total - 5:.2f}:d=5"
                            # the music steps aside while the narrator sings
                            + "".join(f",volume=enable='between(t,{a - 1:.2f},{b + 1:.2f})':volume=0.12" for a, b in songs),
                            "-c:a", "aac", "-b:a", "128k", str(folder / "music.m4a")], check=True)

    # Visuals: anchor each to the start of its segment / card. Real photographs (from
    # tools/photos.py) are copied in and labelled as photographs, never as illustrations.
    starts = {str(s["key"]): s["start"] for s in segs}
    photos = {}
    pj = ROOT / "archive" / "derived" / "photos" / "photos.json"
    if pj.exists():
        photos = {p["id"]: p for p in json.loads(pj.read_text(encoding="utf-8"))}
    visuals = []
    for v in cfg["visuals"]:
        at = starts[str(v["seg"])]
        v = dict(v)
        if "photo" in v:
            ph = photos[v["photo"]]
            (folder / "photos").mkdir(exist_ok=True)
            shutil.copy2(pj.parent / f"{ph['id']}.jpg", folder / "photos" / f"{ph['id']}.jpg")
            v["src"] = f"photos/{ph['id']}.jpg"
            v["label"] = f"Photograph · {ph['caption']} · {ph['date']}"
        elif "src" in v:
            v["label"] = "Illustration · imagined scene"
        # "delay": seconds after the anchor, e.g. a painting at a card, then the real photo 3 s later
        visuals.append({**v, "at": (max(at - 0.4, 0) if visuals else 0) + v.get("delay", 0)})

    visuals.sort(key=lambda v: v["at"])  # the player expects them in time order

    # Insets: a real photo laid over the current picture for a few seconds (a print in the corner),
    # so more family photos can appear without interrupting the paintings or the story.
    insets = []
    for v in cfg.get("insets", []):
        ph = photos[v["photo"]]
        (folder / "photos").mkdir(exist_ok=True)
        shutil.copy2(pj.parent / f"{ph['id']}.jpg", folder / "photos" / f"{ph['id']}.jpg")
        insets.append({"src": f"photos/{ph['id']}.jpg", "label": f"{ph['caption']} · {ph['date']}",
                       "at": starts[str(v["seg"])] + v.get("delay", 1.0), "seconds": v.get("seconds", 6.5),
                       "side": v.get("side", "right")})
    clips = [p for p in pieces if p[0] == "clip" and len(p) == 3]  # interview passages (not songs)
    story = {
        "audio": "audio.m4a",
        "style": cfg.get("style"),  # "bergman": black and white, dips to black, slow push-ins
        "music": "music.m4a" if cfg.get("music") else None,
        "title_hi": cfg["title_hi"], "title_en": cfg["title_en"], "place": cfg["place"],
        "byline": cfg["byline"], "speakerName": cfg["speakerName"], "note": cfg["note"],
        "quote": cfg["quote"], "credit": cfg.get("credit", ""), "places": cfg.get("places", {}), "images": visuals, "insets": insets, "segments": segs,
        "source": (f"Source: {cfg['recording_id']}, {mmss(clips[0][1])}–{mmss(clips[-1][2])}, "
                   f"{len(clips)} passages, questions removed<br>"
                   "Transcript: AI draft, unreviewed<br>"
                   "Images: AI illustrations, not photographs · Map: locations approximate"),
    }
    (folder / "story.js").write_text("window.STORY = " + json.dumps(story, ensure_ascii=False, indent=1) + ";\n",
                                     encoding="utf-8")
    print(f"{folder / 'story.js'}: {len(segs)} lines, {len(clips)} passages, "
          f"{sum(1 for x, y in mutes if any(c[1] <= x < c[2] for c in clips))} backchannels muted, "
          f"edited length {t:.0f}s")


if __name__ == "__main__":
    main()
