"""Extract a reviewable list of life events from the interview transcripts.

Reads every archive/derived/REC-*/transcript.*.chunked.json and asks Gemini for structured events,
each linked back to the recording and time range it comes from. Nothing is invented: dates are
marked "stated", "approximate" or "inferred". Output: archive/derived/events.json (machine draft,
for human review; never overwrite reviewed data with it).

Usage:
    python tools/extract_events.py
"""

import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import family_context, load_key  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "gemini-pro-latest"

PROMPT = """You are helping build a private family oral-history archive. Below are transcripts of interviews
in which a son (INTERVIEWER) asks his father (DAD) about his life. The transcript has errors; words in
[?..?] are uncertain. Each line is: recording id | start-end seconds | speaker | Hindi | English.

Known context (from the family, private):
""" + family_context() + """

Task: list the significant EVENTS and periods of DAD's life that are discussed, in chronological order.

Rules (this is a historical record):
- Use only what is said. Never invent events, names, places or dates.
- year: the best year for the event, or null. date_basis: "stated" (he says the year), "approximate"
  (he gives an age/class that places it roughly) or "inferred" (you worked it out from other facts; explain
  in date_note). Keep date_note short.
- sources: the recording id and the start/end seconds of the passage(s) where it is discussed. Prefer
  the passage where DAD tells it best; at most 3 sources per event. Times must come from the transcript.
- quote_hi / quote_en: one short, characterful line DAD actually says about it (copied from the transcript).
- If recollections conflict (e.g. two different years), keep both in conflict_note; do not resolve them.
- 10 to 25 events. Merge tiny details into the event they belong to.
"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "events": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "id": {"type": "STRING"},
            "title_en": {"type": "STRING"}, "title_hi": {"type": "STRING"},
            "summary_en": {"type": "STRING"},
            "year": {"type": "INTEGER", "nullable": True},
            "year_end": {"type": "INTEGER", "nullable": True},
            "date_basis": {"type": "STRING", "enum": ["stated", "approximate", "inferred", "unknown"]},
            "date_note": {"type": "STRING"},
            "life_stage": {"type": "STRING", "enum": ["childhood", "school", "training", "army", "marriage",
                                                      "family", "later life", "other"]},
            "places": {"type": "ARRAY", "items": {"type": "STRING"}},
            "people": {"type": "ARRAY", "items": {"type": "STRING"}},
            "quote_hi": {"type": "STRING"}, "quote_en": {"type": "STRING"},
            "conflict_note": {"type": "STRING"},
            "sources": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                "recording": {"type": "STRING"}, "start": {"type": "NUMBER"}, "end": {"type": "NUMBER"}},
                "required": ["recording", "start", "end"]}},
        }, "required": ["id", "title_en", "title_hi", "summary_en", "date_basis", "life_stage", "sources"]}},
    },
    "required": ["events"],
}


def main() -> None:
    lines = []
    for f in sorted((ROOT / "archive" / "derived").glob("REC-*/transcript.*.chunked.json")):
        rec = f.parent.name
        for s in json.loads(f.read_text(encoding="utf-8"))["segments"]:
            lines.append(f"{rec} | {s['start']:.0f}-{s['end']:.0f} | {s['speaker']} | {s['text_hi']} | {s['text_en']}")
    body = {"contents": [{"parts": [{"text": PROMPT + "\n\nTRANSCRIPTS:\n" + "\n".join(lines)}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json",
                                 "responseSchema": SCHEMA}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=900))
    events = json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])["events"]
    out = ROOT / "archive" / "derived" / "events.json"
    out.write_text(json.dumps({"status": "machine draft, unreviewed", "model": MODEL, "events": events},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    for e in events:
        y = e.get("year") or "?"
        src = ", ".join(f"{s['recording'][-3:]}@{int(s['start']) // 60}:{int(s['start']) % 60:02d}" for s in e["sources"])
        print(f"{y!s:>5} [{e['date_basis'][:5]}] {e['title_en']}  ({src})")
    print(f"{len(events)} events -> {out}")


if __name__ == "__main__":
    main()
