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
:root{--bg1:#4f46e5;--bg2:#06b6d4;--card:#fff;--text:#1e293b;--muted:#64748b;--accent:#4f46e5}
@media(prefers-color-scheme:dark){:root{--card:#1e293b;--text:#f1f5f9;--muted:#94a3b8;--accent:#818cf8}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;
font-family:"Noto Sans Thai",system-ui,-apple-system,"Segoe UI",sans-serif;
background:linear-gradient(135deg,var(--bg1),var(--bg2));color:var(--text)}
.card{background:var(--card);border-radius:24px;padding:40px 32px;width:100%;max-width:380px;text-align:center;
box-shadow:0 20px 50px rgba(0,0,0,.25)}
h1{margin:0;font-size:1rem;font-weight:600;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
#n{font-size:6.5rem;font-weight:800;line-height:1.1;margin:.15em 0;color:var(--accent);
font-variant-numeric:tabular-nums;transition:transform .15s}
#n.bump{transform:scale(1.15)}
.time{color:var(--muted);font-size:.9rem;margin:0 0 28px}
.btns{display:flex;gap:12px}
button{flex:1;font:inherit;font-size:1.1rem;font-weight:600;padding:.85em 0;border:0;border-radius:14px;
cursor:pointer;transition:transform .1s,box-shadow .2s,opacity .2s}
button:active{transform:scale(.96)}
button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
#inc{background:var(--accent);color:#fff;box-shadow:0 6px 16px rgba(79,70,229,.4)}
#inc:hover{box-shadow:0 8px 22px rgba(79,70,229,.55)}
#rst{background:transparent;color:var(--muted);border:2px solid var(--muted);opacity:.85}
#rst:hover{opacity:1}
</style></head><body>
<main class="card">
<h1>Counter</h1>
<p id="n">-</p>
<p class="time">คลิกล่าสุด: <span id="t">-</span></p>
<div class="btns">
<button id="inc" onclick="act('increment')">นับเลข +</button>
<button id="rst" onclick="act('reset')">รีเซ็ต</button>
</div>
</main>
<script>
function show(s){n.textContent=s.current_number;t.textContent=s.last_click_time||"-";
n.classList.add("bump");setTimeout(()=>n.classList.remove("bump"),150)}
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
