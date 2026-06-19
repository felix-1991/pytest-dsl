from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


USER = {"id": 1001, "username": "api_demo", "role": "tester"}
TOKEN = "demo-token-1001"


class MockAPIHandler(BaseHTTPRequestHandler):
    server_version = "pytest-dsl-mock-api/1.0"

    def log_message(self, format, *args):
        print(f"[mock-api] {self.address_string()} - {format % args}")

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/users/1001":
            self._send_json(
                200,
                {"code": 0, "message": "ok", "data": USER},
            )
            return

        if path == "/api/users/1001/profile":
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._send_json(
                    401,
                    {"code": 40101, "message": "missing or invalid token"},
                )
                return
            self._send_json(
                200,
                {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "user_id": 1001,
                        "active": True,
                        "plan": "team",
                    },
                },
            )
            return

        self._send_json(404, {"code": 40401, "message": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/sessions":
            self._send_json(404, {"code": 40401, "message": "not found"})
            return

        payload = self._read_json()
        if payload != {"username": "api_demo", "password": "pytest-dsl"}:
            self._send_json(
                401,
                {"code": 40102, "message": "invalid credentials"},
            )
            return

        self._send_json(
            201,
            {
                "code": 0,
                "message": "login successful",
                "data": {
                    "access_token": TOKEN,
                    "user_id": USER["id"],
                },
            },
        )


def create_server(host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), MockAPIHandler)


def main():
    parser = argparse.ArgumentParser(
        description="pytest-dsl GUI validation mock API"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(
        f"Mock API listening on http://{args.host}:"
        f"{server.server_address[1]}/"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
