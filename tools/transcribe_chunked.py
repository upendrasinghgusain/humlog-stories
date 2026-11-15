"""Transcribe a recording in short chunks so timestamps stay accurate.

Long audio makes the model estimate timestamps; 60-second chunks keep errors to a few seconds.
The original file is only read. Output: archive/derived/<recording-id>/transcript.<model>.chunked.json

Usage:
    python tools/transcribe_chunked.py <audio-file> <recording-id> [model] [chunk-seconds]
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import transcribe as t  # noqa: E402

FFMPEG = shutil.which("ffmpeg") or next(
    (pathlib.Path.home() / "AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe")
).as_posix()


def duration(audio: pathlib.Path) -> float:
    out = subprocess.run([FFMPEG, "-i", str(audio)], capture_output=True, text=True).stderr
    h, m, s = out.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def with_retry(fn, *args):
    for attempt in range(6):
        try:
            return fn(*args)
        except SystemExit as e:
            if "429" in str(e) or "503" in str(e) or "500" in str(e):
                wait = 20 * (attempt + 1)
                print(f"  rate limited, waiting {wait}s")
                time.sleep(wait)
            else:
                raise
    raise SystemExit("giving up after retries")


def main() -> None:
    audio = pathlib.Path(sys.argv[1]).resolve()
    rec_id = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "gemini-pro-latest"
    size = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0

    total = duration(audio)
    segments, start = [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        while start < total:
            chunk = pathlib.Path(tmp) / f"c{int(start):05d}.m4a"
            subprocess.run([FFMPEG, "-v", "error", "-ss", str(start), "-t", str(size), "-i", str(audio),
                            "-ac", "1", "-c:a", "aac", "-b:a", "96k", str(chunk)], check=True)
            print(f"chunk {start:.0f}s / {total:.0f}s")
            res = with_retry(t.transcribe, chunk, model)
            for s in res["segments"]:
                s["start"] = round(s["start"] + start, 2)
                s["end"] = round(min(s["end"], size) + start, 2)
                segments.append(s)
            start += size

    out_dir = t.ROOT / "archive" / "derived" / rec_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"transcript.{model}.chunked.json"
    out.write_text(json.dumps({
        "source": {"file": audio.name, "model": model, "chunk_seconds": size,
                   "duration_seconds": round(total, 2), "created": time.strftime("%Y-%m-%dT%H:%M:%S")},
        "segments": segments,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out} ({len(segments)} segments)")


if __name__ == "__main__":
    main()
