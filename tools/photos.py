"""Prepare family photographs from media/photos.json.

Applies only the edits listed for each photo (straighten, crop, gentle tone) and writes web-sized
copies to archive/derived/photos/<id>.jpg. The originals are only read. Nothing is added or
invented: no retouching of faces, no colourising, no generated content.

Usage:
    python tools/photos.py
"""

import json
import pathlib

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "archive" / "derived" / "photos"
MAX_SIDE = 1600


def describe(edits: dict) -> str:
    parts = []
    if "rotate" in edits:
        parts.append("straightened")
    if "crop" in edits:
        parts.append("cropped")
    if "autocontrast" in edits:
        parts.append("contrast adjusted")
    return ", ".join(parts) or "unedited"


def main() -> None:
    cfg = json.loads((ROOT / "media" / "photos.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for p in cfg["photos"]:
        im = ImageOps.exif_transpose(Image.open(ROOT / p["file"])).convert("RGB")
        e = p.get("edits", {})
        if "rotate" in e:
            im = im.rotate(e["rotate"], resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0))
        if "crop" in e:
            im = im.crop(tuple(e["crop"]))
        if "autocontrast" in e:
            im = ImageOps.autocontrast(im, cutoff=e["autocontrast"], preserve_tone=True)
        if not p.get("full"):  # panoramas keep their full width
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        out = OUT / f"{p['id']}.jpg"
        im.save(out, quality=88, optimize=True, progressive=True)
        p["_edits_text"] = describe(e)
        print(f"{out.name:28} {im.size[0]}x{im.size[1]}  {p['_edits_text']}")
    (OUT / "photos.json").write_text(json.dumps(cfg["photos"], ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
