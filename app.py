#!/usr/bin/env python3
"""Точка входа для Render.com: HTTP-заглушка на порту $PORT + бот в polling."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PORT = int(os.getenv("PORT", "0"))


def keepalive() -> None:
    """Render ждёт открытый порт у web-сервиса. Отдаём заглушку и ничего не делаем."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"BipBom: ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    if PORT:
        HTTPServer(("0.0.0.0", PORT), H).serve_forever()


def main() -> None:
    if PORT:
        threading.Thread(target=keepalive, daemon=True).start()
        time.sleep(1)
    import bot

    bot.main()


if __name__ == "__main__":
    main()
