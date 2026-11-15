"""Transcribe a family interview recording with Gemini.

Originals are only read, never modified. Output goes to archive/derived/<recording-id>/.

Usage:
    python tools/transcribe.py <audio-file> <recording-id> [model]
"""

import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

def family_context() -> str:
    """Private background about the family (names, places, health), kept out of the code:
    media/family-context.md lives with the private archive and is never committed."""
    f = ROOT / "media" / "family-context.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


CONTEXT = """
This is a private family oral-history interview, recorded on a smartphone, in Hindi
(possibly with some regional words and English loanwords).

Speakers:
- INTERVIEWER: the son, asking questions. Clear speech.
- DAD: the father, telling his life story. His speech may be unclear; listen carefully and patiently.

Background from the family (may help with names and places):
""" + family_context()

INSTRUCTIONS = """
Produce a faithful verbatim transcript in Devanagari Hindi.

Rules - these matter more than fluency:
1. Write what is actually said. Keep repetitions, hesitations and colloquial grammar.
   Do NOT polish, summarise or rewrite.
2. NEVER invent words to make a sentence sound complete. This is a historical record.
3. If a word or phrase is unclear, write your best guess wrapped as [?guess?].
   If you cannot guess at all, write [अस्पष्ट].
4. Do not use the "known names" list to force a name where it was not said.
5. Split into short segments (one sentence or phrase each, normally under 15 seconds),
   with accurate start/end timestamps in seconds from the start of the audio.
6. Label each segment's speaker as INTERVIEWER or DAD.
7. Give each segment a confidence: high, medium or low.
8. Also give a plain English translation of each segment (faithful, not polished).
9. Family terms: DAD often names relatives from the INTERVIEWER's point of view.
   "दादा जी" / "दादी" usually mean DAD's own father / mother; "चाचा" may mean DAD's younger
   brother. Translate as e.g. "your grandfather (my father)" when that is clearly meant.
"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "segments": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "start": {"type": "NUMBER"},
                    "end": {"type": "NUMBER"},
                    "speaker": {"type": "STRING", "enum": ["INTERVIEWER", "DAD", "OTHER"]},
                    "text_hi": {"type": "STRING"},
                    "text_en": {"type": "STRING"},
                    "confidence": {"type": "STRING", "enum": ["high", "medium", "low"]},
                },
                "required": ["start", "end", "speaker", "text_hi", "text_en", "confidence"],
            },
        },
        "notes": {"type": "STRING"},
    },
    "required": ["segments"],
}


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not found")


def transcribe(audio: pathlib.Path, model: str) -> dict:
    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": CONTEXT + "\n" + INSTRUCTIONS},
                {"inline_data": {"mime_type": "audio/mp4",
                                 "data": base64.b64encode(audio.read_bytes()).decode()}},
            ],
        }],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    if "transcribe" in model:
        # Transcription-only models don't support JSON mode: describe the format in the prompt.
        del body["generationConfig"]["responseMimeType"], body["generationConfig"]["responseSchema"]
        body["contents"][0]["parts"][0]["text"] += (
            "\nReturn ONLY a JSON object, no markdown, matching this schema:\n"
            + json.dumps(SCHEMA)
        )
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:2000]}")
    text = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
    try:
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        raw = ROOT / "archive" / "derived" / f"raw.{model}.txt"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(text, encoding="utf-8")
        sys.exit(f"Response was not JSON; raw output saved to {raw}")


def main() -> None:
    audio = pathlib.Path(sys.argv[1]).resolve()
    rec_id = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "gemini-3.5-transcribe"

    t0 = time.time()
    result = transcribe(audio, model)
    result["source"] = {"file": audio.name, "model": model,
                        "created": time.strftime("%Y-%m-%dT%H:%M:%S")}

    out_dir = ROOT / "archive" / "derived" / rec_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"transcript.{model}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    segs = result["segments"]
    low = sum(1 for s in segs if s["confidence"] == "low")
    print(f"{out}  ({len(segs)} segments, {low} low-confidence, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
