"""Run a local mock CRM API for the GTM Signal Router demo."""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DATABASE = ROOT / "data/mock_crm.db"


def save_received(payload):
    conn = sqlite3.connect(DATABASE)
    conn.execute("""CREATE TABLE IF NOT EXISTS received_leads (
                    id INTEGER PRIMARY KEY, payload TEXT NOT NULL,
                    received_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("INSERT INTO received_leads (payload) VALUES (?)", (json.dumps(payload),))
    conn.commit()
    conn.close()


class MockCrmHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/v1/leads":
            self.send_error(404, "Use POST /api/v1/leads")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
            save_received(payload)
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return
        body = json.dumps({"status": "received", "crm_record_id": payload.get("crm_record_id")}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), MockCrmHandler)
    print("Mock CRM running at http://127.0.0.1:8765/api/v1/leads")
    print("Press Ctrl+C to stop it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
