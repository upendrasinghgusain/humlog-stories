"""Generate illustrations for a story chapter with a Gemini image model.

These are clearly-labelled reconstructions, never presented as photographs.

Usage:
    python tools/illustrate.py <scenes.json> <out-dir> [model]
scenes.json: {"setting": "place and period", "scenes": [{"id": "path", "prompt": "...", "refs": ["photo.jpg"]}]}
"refs" (optional): photos of the real place, used only as a reference for the painting.
"""

import base64
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import load_key  # noqa: E402

STYLE = (
    "Soft hand-painted watercolour and gouache illustration, like a quiet picture-book memoir. "
    "Muted earthy palette, gentle paper texture, loose edges, warm low light. "
    "{setting}"
    "People shown small, from behind, in silhouette or at a distance - no detailed faces. "
    "No text, no lettering, no borders, no modern objects. Wide cinematic 16:9 composition. "
)


REF_NOTE = ("The attached photograph(s) show the real place today. Use them only as a reference for the "
            "landscape, the shape of the ridge and valley, the layout and the kind of buildings, so the painting "
            "feels like this actual place; paint it in the style above, as it might have looked in the period "
            "described, leaving out anything modern. Do not copy the photograph. ")


MATCH_NOTE = ("The attached photograph shows the real place today. Repaint THIS EXACT VIEW: keep the same composition, "
              "camera position, horizon, ridge lines and the position of the main buildings and trees, so the painting can "
              "dissolve into the photograph. Paint it in the style above, as it would have looked in the period described: "
              "replace modern things as the scene asks and leave out all people, cars, signs and writing. ")


def generate(prompt: str, model: str, setting: str = "", refs: list | None = None, match: bool = False) -> bytes:
    parts = []
    for r in refs or []:
        p = pathlib.Path(r)
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}})
    text = STYLE.replace("{setting}", setting + " " if setting else "") + ((MATCH_NOTE if match else REF_NOTE) if refs else "") + "Scene: " + prompt
    body = {
        "contents": [{"parts": parts + [{"text": text}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"},
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
            for p in resp["candidates"][0]["content"]["parts"]:
                if "inlineData" in p:
                    return base64.b64decode(p["inlineData"]["data"])
            raise SystemExit(f"no image returned: {json.dumps(resp)[:500]}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                time.sleep(20 * (attempt + 1))
                continue
            raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:800]}")
    raise SystemExit("giving up")


def main() -> None:
    # scenes.json: a list of scenes, or {"setting": "place and period", "scenes": [...]}
    data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    scenes = data["scenes"] if isinstance(data, dict) else data
    setting = data.get("setting", "") if isinstance(data, dict) else ""
    out = pathlib.Path(sys.argv[2])
    model = sys.argv[3] if len(sys.argv) > 3 else "gemini-3-pro-image"
    out.mkdir(parents=True, exist_ok=True)
    for s in scenes:
        target = out / f"{s['id']}.png"
        if target.exists():
            print("skip", target.name)
            continue
        # "refs": reference photos of the real place (private, never published), e.g. media/reference/...
        target.write_bytes(generate(s["prompt"], model, setting, s.get("refs"), s.get("match", False)))
        print("ok", target.name)


if __name__ == "__main__":
    main()
