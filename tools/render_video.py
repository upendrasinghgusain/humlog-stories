"""Render a story chapter page to MP4 videos, frame by frame, in parallel.

The page runs in headless Chrome on a *virtual clock*: timers, requestAnimationFrame,
performance.now/Date and all CSS animations are advanced exactly 1/FPS second per frame, then a
screenshot is taken, so every fade and map animation is smooth however slow the capture is.

Each video is split into sections rendered by separate Chrome workers. A worker fast-forwards the
virtual clock (cheap, no screenshots) to its section start, so every section begins in exactly the
state a single continuous render would have. The chapter's audio (Dad's voice + quiet music bed)
is added at the end, offset by the intro hold.

Usage:
    python tools/render_video.py stories/<story-folder> <out-dir> [name=WxH ...] [--workers N] [--seconds S]
    e.g. python tools/render_video.py stories/weekly-journey exports landscape=1920x1080 portrait=1080x1920@2
    (@2 = phone-sized page rendered at 2x pixel density, so text is phone-readable)
"""

import argparse
import base64
import functools
import http.server
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe_chunked import FFMPEG  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = 30
INTRO_HOLD = 5.0   # seconds on the title card before Dad's voice starts
OUTRO_HOLD = 9.0   # seconds on the end card

# Injected before any page script: a controllable clock.
VIRTUAL_TIME = """
(() => {
  let vt = 0;
  // keep the browser's real frame clock: used to wait until a frame has really been drawn
  const realRAF = window.requestAnimationFrame.bind(window);
  window.__drawn = () => new Promise(r => realRAF(() => realRAF(() => r(true))));
  const realNow = Date.now(), timers = new Map(); let nextId = 1, rafQ = [];
  performance.now = () => vt;
  Date.now = () => realNow + vt;
  window.setTimeout = (fn, ms = 0, ...a) => { const id = nextId++; timers.set(id, { at: vt + ms, fn, a }); return id; };
  window.clearTimeout = id => timers.delete(id);
  window.setInterval = (fn, ms = 0, ...a) => { const id = nextId++;
    timers.set(id, { at: vt + ms, fn, a, every: Math.max(ms, 1) }); return id; };
  window.clearInterval = id => timers.delete(id);
  window.requestAnimationFrame = fn => { rafQ.push(fn); return rafQ.length; };
  window.cancelAnimationFrame = () => {};
  const seen = new WeakMap();
  window.__advance = (ms, storyT) => {
    const target = vt + ms;
    for (;;) {
      let best = null;
      for (const [id, t] of timers) if (t.at <= target && (!best || t.at < best[1].at)) best = [id, t];
      if (!best) break;
      const [id, t] = best; vt = Math.max(vt, t.at);
      if (t.every) t.at += t.every; else timers.delete(id);
      try { typeof t.fn === "function" ? t.fn(...t.a) : null; } catch (e) { console.error(e); }
    }
    vt = target;
    if (window.__render) window.__render(storyT);
    const q = rafQ; rafQ = [];
    q.forEach(fn => { try { fn(vt); } catch (e) { console.error(e); } });
    document.getAnimations().forEach(a => {
      if (!seen.has(a)) { seen.set(a, vt); a.pause(); }
      a.currentTime = vt - seen.get(a);
    });
  };
  // fast-forward many frames in one call (no screenshots)
  window.__skip = (n, msPerFrame, t0, dt) => { for (let i = 0; i < n; i++) window.__advance(msPerFrame, t0 + i * dt); };
})();
"""


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 256  # default is 5: several Chromes starting at once get refused -> broken images


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(folder: pathlib.Path) -> int:
    httpd = Server(("127.0.0.1", 0),
                                            functools.partial(QuietHandler, directory=str(folder)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]


def duration(f: pathlib.Path) -> float:
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)",
                  subprocess.run([FFMPEG, "-i", str(f)], capture_output=True, text=True).stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


# ---------------------------------------------------------------- worker (one section)

def worker(port: int, w: int, h: int, start: int, end: int, frame_dir: pathlib.Path, dur: float,
           scale: int = 1) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--ignore-gpu-blocklist"])
        # The viewport is the CSS size; screenshots come out at w*scale x h*scale pixels.
        page = browser.new_page(viewport={"width": w // scale, "height": h // scale}, device_scale_factor=scale)
        page.add_init_script(VIRTUAL_TIME + f"\nwindow.__DUR = {dur};")
        page.goto(f"http://127.0.0.1:{port}/index.html?video=1", wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        # Maps must finish loading (in real time) before the virtual clock moves, or a map that
        # comes on screen during a fast-forward starts its animation late.
        # The maps' own loading runs on the virtual clock too, so pump timers and animation
        # frames (without moving story time) until both maps report loaded.
        for _ in range(600):
            if page.evaluate(f"__advance(0, {-INTRO_HOLD}); window.__mapsLoaded && __mapsLoaded()"):
                break
            page.wait_for_timeout(100)
        else:
            raise SystemExit("maps did not load within 60 s")
        # Every painting must have loaded; re-request any that failed.
        for _ in range(50):
            broken = page.evaluate("""[...document.querySelectorAll('img.pic')].filter(i => i.complete && !i.naturalWidth)
                .map(i => { i.src = i.getAttribute('src') + '?retry=' + Date.now(); return i.getAttribute('src'); }).length""")
            pending = page.evaluate("[...document.querySelectorAll('img.pic')].filter(i => !i.complete).length")
            if not broken and not pending:
                break
            page.wait_for_timeout(200)
        else:
            raise SystemExit("paintings failed to load")
        cdp = page.context.new_cdp_session(page)
        ms = 1000 / FPS
        # Resume: jump straight to the first frame of this section that isn't on disk yet.
        first = next((i for i in range(start, end) if not (frame_dir / f"f{i:06d}.jpg").exists()), end)
        if first:
            page.evaluate(f"__skip({first}, {ms}, {-INTRO_HOLD}, {1 / FPS})")
            page.wait_for_timeout(1500)  # let any map on screen fetch its tiles
        for i in range(first, end):
            target = frame_dir / f"f{i:06d}.jpg"
            page.evaluate(f"__advance({ms}, {i / FPS - INTRO_HOLD})")
            # A map on screen: keep running animation frames (without moving the clock) until
            # its tiles are loaded and drawn, so no frame shows a blank or half-drawn map.
            for _ in range(80):
                if page.evaluate(f"__mapsReady()"):
                    break
                page.wait_for_timeout(40)
                page.evaluate(f"__advance(0, {i / FPS - INTRO_HOLD})")
            # Under memory pressure (several Chromes at once) Chrome may drop decoded images and
            # redraw them later; make sure every visible painting is decoded before the screenshot.
            page.evaluate("__imagesReady()")
            page.evaluate(f"__advance(0, {i / FPS - INTRO_HOLD})")  # one more draw with everything loaded
            # Wait until Chrome has really drawn this frame (two real frames). Without this, a busy
            # machine (several Chromes at once) screenshots before paintings are rasterised: blank.
            page.evaluate("__drawn()")
            shot = cdp.send("Page.captureScreenshot",
                            {"format": "jpeg", "quality": 92, "optimizeForSpeed": True})
            target.write_bytes(base64.b64decode(shot["data"]))
        browser.close()


# ---------------------------------------------------------------- orchestration

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("out_dir")
    ap.add_argument("formats", nargs="*", default=["landscape=1920x1080", "portrait=1080x1920@2"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seconds", type=float, help="render only the first N seconds (testing)")
    ap.add_argument("--fresh", action="store_true", help="discard cached frames from earlier runs")
    ap.add_argument("--worker", nargs=8, help=argparse.SUPPRESS)  # port w h start end dir duration scale
    a = ap.parse_args()

    if a.worker:
        port, w, h, s, e = (int(x) for x in a.worker[:5])
        worker(port, w, h, s, e, pathlib.Path(a.worker[5]), float(a.worker[6]), int(a.worker[7]))
        return

    folder = (ROOT / a.folder).resolve()
    out_dir = (ROOT / a.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    story = json.loads(re.search(r"\{.*\}", (folder / "story.js").read_text(encoding="utf-8"), re.S)[0])
    audio_dur = duration(folder / story["audio"])
    total = INTRO_HOLD + audio_dur + OUTRO_HOLD
    if a.seconds:
        total = min(total, a.seconds)
    n_frames = int(total * FPS)
    port = serve(folder)
    title = story["title_en"].title()

    def parse(f):  # name=WxH[@scale]
        name, size = f.split("=")
        size, _, scale = size.partition("@")
        w, h = (int(x) for x in size.lower().split("x"))
        return name, w, h, int(scale or 1)
    formats = [parse(f) for f in a.formats]
    work = ROOT / ".render-cache" / folder.name
    if a.fresh:
        shutil.rmtree(work, ignore_errors=True)
    # Starting a worker costs ~1 min (Chrome + map tiles), so split only the frames still missing
    # (earlier runs are cached) into one contiguous section per worker.
    runs = []  # (name, w, h, dir, start, end) contiguous runs of missing frames
    for name, w, h, sc in formats:
        d = work / f"{name}-{w}x{h}"
        d.mkdir(parents=True, exist_ok=True)
        s = None
        for i in range(n_frames + 1):
            missing = i < n_frames and not (d / f"f{i:06d}.jpg").exists()
            if missing and s is None:
                s = i
            elif not missing and s is not None:
                runs.append((name, w, h, sc, d, s, i))
                s = None
    left = sum(e - s for *_, s, e in runs)
    per = max(-(-left // a.workers), 1)
    jobs = []
    for name, w, h, sc, d, s, e in runs:
        while s < e:
            jobs.append((name, w, h, sc, s, min(s + per, e), d))
            s += per

    t0 = time.time()
    done = [0]

    def run(job):
        name, w, h, sc, s, e, d = job
        for attempt in range(3):
            r = subprocess.run([sys.executable, "-X", "utf8", __file__, a.folder, a.out_dir,
                                "--worker", str(port), str(w), str(h), str(s), str(e), str(d), str(audio_dur), str(sc)])
            if r.returncode == 0 and all((d / f"f{i:06d}.jpg").exists() for i in range(s, e)):
                break
            print(f"  {name} frames {s}-{e} failed (attempt {attempt + 1}), retrying", flush=True)
        else:
            raise SystemExit(f"{name} frames {s}-{e} failed 3 times")
        done[0] += 1
        print(f"  [{time.time() - t0:5.0f}s] {name} frames {s}-{e} done ({done[0]}/{len(jobs)})", flush=True)

    print(f"{len(jobs)} sections, {a.workers} workers, {n_frames} frames per video")
    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(run, jobs))

    delay = int(INTRO_HOLD * 1000)
    a_in = ["-i", str(folder / story["audio"])]
    mix = f"[1]adelay={delay}|{delay}[v]"
    if story.get("music"):
        a_in += ["-i", str(folder / story["music"])]
        mix += f";[2]adelay={delay}|{delay}[m];[v][m]amix=inputs=2:normalize=0:duration=longest"
    mix += f",apad=whole_dur={total:.2f}[a]"
    for name, w, h, _ in formats:
        out = out_dir / f"{title} - {name}.mp4"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-framerate", str(FPS),
                        "-i", str(work / f"{name}-{w}x{h}" / "f%06d.jpg"), *a_in,
                        "-filter_complex", mix, "-map", "0:v", "-map", "[a]",
                        "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                        "-profile:v", "high", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}",
                        "-movflags", "+faststart", str(out)], check=True)
        print(f"{out}  ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
