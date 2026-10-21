#!/usr/bin/env python3
"""Preview the GitHub Pages site locally under the same /qtr/ base path.

    python scripts/dev/serve_site.py            # http://127.0.0.1:8000/qtr/
    python scripts/dev/serve_site.py --port 9000

Paths outside /qtr/ return docs/404.html with status 404, like GitHub Pages.
Stop with Ctrl+C. No build step: the site is static files in docs/.
"""

import argparse
import functools
import http.server
import pathlib
import socketserver

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs"
BASE = "/qtr"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == BASE:  # GitHub Pages redirects /qtr -> /qtr/
            self.send_response(301)
            self.send_header("Location", BASE + "/")
            self.end_headers()
            return
        super().do_GET()

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if not path.startswith(BASE + "/"):
            return str(DOCS / "__missing__")
        rel = path[len(BASE) + 1 :] or "index.html"
        target = (DOCS / rel).resolve()
        if DOCS.resolve() not in target.parents and target != DOCS.resolve():
            return str(DOCS / "__missing__")  # no path traversal outside docs/
        return str(target)

    def send_error(self, code, message=None, explain=None):
        if code == 404 and (DOCS / "404.html").exists():
            body = (DOCS / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    handler = functools.partial(Handler, directory=str(DOCS))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {DOCS} at http://{args.host}:{args.port}{BASE}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
