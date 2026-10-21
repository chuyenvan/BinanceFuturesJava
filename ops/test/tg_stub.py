#!/usr/bin/env python3
"""Stub Telegram cho test watchdog: nghe 127.0.0.1:<port>, ghi moi POST /bot<token>/sendMessage vao file JSONL
(token CHI so khop voi gia tri ky vong => ghi token_ok, KHONG ghi token). argv: port out.jsonl expected_token"""
import json
import logging
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
PORT, OUT, TOK = int(sys.argv[1]), sys.argv[2], sys.argv[3]


class H(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length", "0"))
        body = urllib.parse.parse_qs(self.rfile.read(n).decode())
        rec = {"token_ok": self.path == "/bot%s/sendMessage" % TOK,
               "chat_id": body.get("chat_id", [""])[0], "text": body.get("text", [""])[0]}
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", PORT), H).serve_forever()
