"""Ask Gemini to listen to an edited story clip and report interviewer voice or clipped words.

Usage:
    python tools/check_edit.py stories/<story-folder>/audio.m4a
"""

import base64
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import load_key  # noqa: E402

PROMPT = """This audio is an edit of a Hindi family interview. It should contain ONLY one speaker:
an elderly man whose speech may be unclear, in short passages separated by pauses and silent gaps.
A second, younger male voice (the interviewer, his son) should have been removed.
Listen carefully and report every problem:
- "interviewer_voice": any moment the younger voice is audible (including "hmm", "haan"), and whether it
  overlaps the old man's words.
- "clipped_start" / "clipped_end": a word audibly cut off at the start or end of a passage.
Return JSON: {"issues": [{"time": seconds, "type": "...", "overlaps": true|false, "detail": "..."}]}"""


def main() -> None:
    audio = pathlib.Path(sys.argv[1])
    body = {"contents": [{"parts": [{"text": PROMPT},
                                    {"inline_data": {"mime_type": "audio/mp4",
                                                     "data": base64.b64encode(audio.read_bytes()).decode()}}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=600))
    issues = json.loads(resp["candidates"][0]["content"]["parts"][0]["text"])["issues"]
    for i in issues:
        print(f"{i['time']:6.1f}s  {i['type']:<17} overlaps={i.get('overlaps')}  {i['detail']}")
    print(f"{len(issues)} issues")


if __name__ == "__main__":
    main()
