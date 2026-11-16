"""Set each passage's cut points from turns.json (written by tools/turns.py).

For every passage in story.config.json:
- start = where the narrator's first utterance begins, end = where his last one ends before the next
  real question (an OTHER utterance longer than 1 s);
- short OTHER utterances inside the passage ("हम्म", "हाँ") are added to the "mute" list;
- both cut points are nudged onto the nearest real silence (never further than 0.3 s), so words are
  not clipped.
The config is updated in place; run tools/build_story.py afterwards.

Usage:
    python tools/refine_cuts.py stories/<story-folder> [--dry-run]
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_story import silences  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    folder = (ROOT / sys.argv[1]).resolve()
    dry = "--dry-run" in sys.argv
    cfg_file = folder / "story.config.json"
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    turns = json.loads((folder / "turns.json").read_text(encoding="utf-8"))
    tr = json.loads((ROOT / cfg["transcript"]).read_text(encoding="utf-8"))["segments"]
    original = ROOT / cfg["audio_original"]
    mutes = [m for m in cfg.get("mute", []) if m[2:] != ["auto"]]  # keep hand-made mutes

    for item in cfg["edit"]:
        if "segs" not in item:
            continue
        key = ",".join(map(str, item["segs"]))
        if key not in turns:
            print(f"{key:14} no turn timings, left as is")
            continue
        lo, hi = tr[item["segs"][0]]["start"], tr[item["segs"][-1]]["end"]
        utts = sorted(turns[key]["utterances"], key=lambda u: u["start"])
        # the narrator's utterances that belong to THIS passage: their middle lies inside its transcript span
        mine = [u for u in utts if u["speaker"] == "ELDER" and lo - 0.7 <= (u["start"] + u["end"]) / 2 <= hi + 0.7]
        if not mine:
            print(f"{key:14} narrator not found in turns, left as is")
            continue
        a, b = mine[0]["start"], mine[0]["end"]
        inner = []
        for u in utts:
            if u["start"] < a or u is mine[0]:
                continue
            if u["speaker"] == "OTHER":
                if u["end"] - u["start"] > 1.0:
                    break          # a real question: the passage ends before it
                inner.append(u)    # maybe a backchannel inside the passage
            elif u in mine:
                b = u["end"]
            else:
                break              # narrator words from the next passage
        inner = [u for u in inner if u["end"] <= b]
        # Window timings drift by up to ~1 s, so never cross the transcript's own neighbouring questions.
        first, last = item["segs"][0], item["segs"][-1]
        prev_q = next((tr[i]["end"] for i in range(first - 1, max(first - 4, -1), -1) if tr[i]["speaker"] != "DAD"), None)
        next_q = next((tr[i]["start"] for i in range(last + 1, min(last + 4, len(tr))) if tr[i]["speaker"] != "DAD"), None)
        if prev_q is not None:
            a = max(a, prev_q - 0.3)
        if next_q is not None:
            b = min(b, next_q + 0.3)
        if b - a < 0.6 * (hi - lo) - 0.5:
            print(f"{key:14} turns cover too little of the passage ({b - a:.1f}s of {hi - lo:.1f}s), left as is")
            continue
        sil = silences(original, a - 2, b + 2, noise=-32, d=0.12)
        s_end = [e for s, e in sil if a - 0.3 <= e <= a + 0.2]
        s_start = [s for s, e in sil if b - 0.2 <= s <= b + 0.3]
        a2 = round((max(s_end) - 0.06) if s_end else a, 2)
        b2 = round((min(s_start) + 0.12) if s_start else b, 2)
        old = (item.get("start"), item.get("end"))
        item["start"], item["end"] = a2, b2
        for u in inner:
            mutes.append([round(u["start"] - 0.05, 2), round(u["end"] + 0.05, 2), "auto"])
        print(f"{key:14} {old[0]}-{old[1]}  ->  {a2}-{b2}" + (f"   mute {len(inner)}" if inner else ""))

    cfg["mute"] = mutes
    if not dry:
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
