"""Локальный HTTPS-сервер для WebApp (работает в паре с ngrok).

Запуск: py serve.py 8080  →  http://127.0.0.1:8080/
Наружу страницу отдаёт ngrok: webapp.cmd
"""

import http.server
import socketserver
import sys
from functools import partial


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print("[web]", fmt % args)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    handler = partial(Handler, directory="web")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"WebApp: http://127.0.0.1:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
