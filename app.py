from flask import (
    Flask, request, session, redirect,
    url_for, render_template, g, make_response
)
import sqlite3
from datetime import datetime

# =====================
# 기본 설정
# =====================
APP_SECRET_KEY = "MAPARAM-AND-ASHER-HARROW"
ACCESS_TOKEN = "MAPARAM-AND-ASHER-HARROW"
DB_PATH = "space.db"

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

# =====================
# DB 관리
# =====================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# =====================
# 비공개 링크(token) 체크
# =====================
def check_token():
    token = request.args.get("token") or session.get("token")
    if token != ACCESS_TOKEN:
        return False
    session["token"] = token
    return True

@app.before_request
def require_private_link():
    if request.path.startswith("/static") or request.path in ["/robots.txt", "/favicon.ico"]:
        return None

    ok = check_token()
    if not ok:
        return ("접근 불가: 올바른 비공개 링크(token)가 필요합니다.", 403)

    return None


@app.after_request
def add_noindex_headers(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return resp

@app.get("/robots.txt")
def robots():
    resp = make_response("User-agent: *\nDisallow: /\n", 200)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp

# =====================
# 라우트
# =====================

# 첫 진입 → 선택 페이지
@app.get("/")
def home():
    return redirect(url_for("select", token=session.get("token")))

# 유저 선택 페이지
@app.get("/select")
def select():
    return render_template("select.html", character=session.get("character"))

# 유저 선택 처리
@app.post("/select")
def select_post():
    character = request.form.get("user")
    if character not in ["H", "M"]:
        return ("잘못된 선택입니다.", 400)

    session["character"] = character
    return redirect(url_for("send", token=session.get("token")))

# 입력 페이지
@app.get("/send")
def send():
    character = session.get("character")
    if character not in ["H", "M"]:
        return redirect(url_for("select", token=session.get("token")))

    return render_template("send.html", character=character)

# 메시지 전송 처리
@app.post("/send")
def send_post():
    character = session.get("character")
    if character not in ["H", "M"]:
        return redirect(url_for("select", token=session.get("token")))

    content = (request.form.get("content") or "").strip()
    content = " ".join(content.splitlines()).strip()

    if not content:
        return ("메시지가 비어있습니다.", 400)
    if len(content) > 240:
        return ("메시지는 240자 이하로 해주세요.", 400)

    db = get_db()
    db.execute(
        "INSERT INTO messages (sender, content, created_at) VALUES (?, ?, ?)",
        (character, content, datetime.utcnow().isoformat(timespec="seconds") + "Z")
    )
    db.commit()

    return redirect(url_for("log", token=session.get("token")))

# 로그 페이지
@app.get("/log")
def log():
    db = get_db()
    rows = db.execute(
        "SELECT sender, content, created_at FROM messages ORDER BY id ASC"
    ).fetchall()

    logs = [f"[{r['sender']}] {r['content']}" for r in rows]

    return render_template(
        "log.html",
        rows=rows,
        logs=logs,
        character=session.get("character")
    )


# =====================
# 실행
# =====================
import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
