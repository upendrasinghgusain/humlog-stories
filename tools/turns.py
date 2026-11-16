"""Find exact speaker turns around each passage of a chapter, to set precise cut points.

The chunked transcripts are accurate to about a second, which is not enough when the interviewer
answers within a fraction of a second. This sends a short window around each passage to Gemini and
asks for every utterance with its speaker and times to a tenth of a second.

Usage:
    python tools/turns.py stories/<story-folder> [pad_seconds]
Writes stories/<story-folder>/turns.json (private, like the rest of the chapter).
"""

import base64
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import load_key  # noqa: E402
from transcribe_chunked import FFMPEG  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "gemini-pro-latest"
PROMPT = """This is a short excerpt of a Hindi family interview. Speakers:
- ELDER: the elderly narrator telling their life story (an older man or woman).
- OTHER: anyone else (the interviewer, a younger man, or anyone in the room).
List every utterance in order, including short ones like "हम्म", "हाँ", "ओके".
For each give the speaker, the Hindi text, and start and end times in seconds from the start
of THIS excerpt, as precisely as you can (to 0.1 s). Do not merge different speakers.
The ELDER's expected words are roughly: "{hint}"."""
SCHEMA = {"type": "OBJECT", "properties": {"utterances": {"type": "ARRAY", "items": {
    "type": "OBJECT", "properties": {"speaker": {"type": "STRING", "enum": ["ELDER", "OTHER"]},
                                     "text": {"type": "STRING"}, "start": {"type": "NUMBER"},
                                     "end": {"type": "NUMBER"}},
    "required": ["speaker", "text", "start", "end"]}}}, "required": ["utterances"]}


def ask(wav: bytes, hint: str) -> list:
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav).decode()}},
                                    {"text": PROMPT.replace("{hint}", hint)}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                                 data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            return json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])["utterances"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                time.sleep(15 * (attempt + 1))
                continue
            raise
        except (TimeoutError, urllib.error.URLError):
            time.sleep(10)
    raise SystemExit("giving up")


def main() -> None:
    folder = (ROOT / sys.argv[1]).resolve()
    pad = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    cfg = json.loads((folder / "story.config.json").read_text(encoding="utf-8"))
    tr = json.loads((ROOT / cfg["transcript"]).read_text(encoding="utf-8"))["segments"]
    original = ROOT / cfg["audio_original"]
    saved = folder / "turns.json"
    out = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}  # resume
    with tempfile.TemporaryDirectory() as tmp:
        for item in cfg["edit"]:
            if "segs" not in item or ",".join(map(str, item["segs"])) in out:
                continue
            idx = item["segs"]
            a, b = tr[idx[0]]["start"] - pad, tr[idx[-1]]["end"] + pad
            wav = pathlib.Path(tmp) / "w.wav"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", str(original),
                            "-ac", "1", "-ar", "16000", str(wav)], check=True)
            hint = " ".join(tr[i]["text_hi"] for i in idx)
            utts = ask(wav.read_bytes(), hint)
            for u in utts:
                u["start"] = round(u["start"] + a, 2)
                u["end"] = round(u["end"] + a, 2)
            out[",".join(map(str, idx))] = {"window": [round(a, 2), round(b, 2)], "utterances": utts}
            print(f"segs {idx}  window {a:.1f}-{b:.1f}")
            for u in utts:
                print(f"   {u['start']:7.2f}-{u['end']:7.2f} {u['speaker']:5} {u['text']}")
            saved.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
