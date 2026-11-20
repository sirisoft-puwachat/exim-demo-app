"""Webapp นับเลขอย่างง่าย — เก็บสถานะในไฟล์ JSON เท่านั้น (ไม่ใช้ DB), ใช้ stdlib ล้วน"""
import fcntl
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COUNT_FILE = os.environ.get("COUNT_FILE", "./data/count.json")
PORT = int(os.environ.get("PORT", "8080"))
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _now():
    return datetime.now().strftime(TIME_FMT)


def update_state(mutate=None):
    """อ่าน (และแก้ไขถ้ามี mutate) ไฟล์ภายใต้ flock เพื่อกัน race ระหว่าง request/pod

    เขียนทับไฟล์ตรงๆ (ไม่ใช้ temp+rename) เพราะถ้า mount แบบ subPath บน PVC
    การ rename ทับไฟล์จะล้มเหลว
    """
    d = os.path.dirname(os.path.abspath(COUNT_FILE))
    os.makedirs(d, exist_ok=True)
    fd = os.open(COUNT_FILE, os.O_RDWR | os.O_CREAT, 0o644)
    with os.fdopen(fd, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            state = json.loads(f.read() or "null")
            if not isinstance(state, dict) or "current_number" not in state:
                raise ValueError
        except ValueError:
            state = {"current_number": 0, "last_click_time": None}
        if mutate:
            mutate(state)
            f.seek(0)
            f.truncate()
            json.dump(state, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        return state


def _increment(s):
    s["current_number"] += 1
    s["last_click_time"] = _now()


def _reset(s):
    s["current_number"] = 0
    s["last_click_time"] = _now()


PAGE = """<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Counter</title>
<style>
body{font-family:sans-serif;text-align:center;margin-top:12vh}
#n{font-size:6rem;margin:0}
button{font-size:1.2rem;padding:.6em 1.6em;margin:.4em}
</style></head><body>
<p id="n">-</p>
<p>คลิกล่าสุด: <span id="t">-</span></p>
<button onclick="act('increment')">นับเลข +</button>
<button onclick="act('reset')">รีเซ็ต</button>
<script>
function show(s){n.textContent=s.current_number;t.textContent=s.last_click_time||"-"}
function act(a){fetch("/api/"+a,{method:"POST"}).then(r=>r.json()).then(show)}
fetch("/api/count").then(r=>r.json()).then(show)
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, state):
        self._send(200, json.dumps(state, ensure_ascii=False))

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE, "text/html")
        elif self.path == "/api/count":
            self._json(update_state())
        elif self.path == "/healthz":
            self._send(200, "ok", "text/plain")
        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if self.path == "/api/increment":
            self._json(update_state(_increment))
        elif self.path == "/api/reset":
            self._json(update_state(_reset))
        else:
            self._send(404, '{"error":"not found"}')


if __name__ == "__main__":
    print(f"listening on :{PORT}, COUNT_FILE={COUNT_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
