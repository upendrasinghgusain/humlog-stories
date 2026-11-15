"""Serve the built site locally, with HTTP Range support so audio can seek.

Usage:
    python tools/serve.py [folder] [port]      (defaults: site 8770)
Then open http://127.0.0.1:8770/
"""

import functools
import http.server
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript; charset=utf-8", ".m4a": "audio/mp4", ".mp4": "video/mp4"}

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        path = pathlib.Path(self.translate_path(self.path))
        m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
        if not m or not path.is_file():
            return super().send_head()  # directories -> index.html, plain files -> 200
        size = path.stat().st_size
        start = int(m[1]) if m[1] else max(size - int(m[2] or 0), 0)
        end = min(int(m[2]), size - 1) if m[1] and m[2] else size - 1
        f = path.open("rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self.range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "range_left", None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            chunk = source.read(min(64 * 1024, left))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (ConnectionResetError, BrokenPipeError):
                break  # the browser cancelled (normal when seeking)
            left -= len(chunk)

    def log_message(self, *a):
        pass


def main() -> None:
    folder = (ROOT / (sys.argv[1] if len(sys.argv) > 1 else "site")).resolve()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8770
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(folder)))
    print(f"Serving {folder} at http://127.0.0.1:{port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
