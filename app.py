from flask import (
    Flask, request, session, redirect,
    url_for, render_template, g, make_response
)
import sqlite3
from datetime import datetime
import os

# =====================
# 기본 설정
# =====================
APP_SECRET_KEY = "MAPARAM-AND-ASHER-HARROW"

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

# =====================
# 로그인 계정 (2명)
# =====================
USERS = {
    "asher": {
        "password": "ABC_hello_itsme",
        "role": "H"
    },
    "param": {
        "password": "MHM_thsis_vela",
        "role": "M"
    }
}

# =====================
# DB 경로 (Render 안전)
# =====================
os.makedirs(app.instance_path, exist_ok=True)
DB_PATH = os.path.join(app.instance_path, "space.db")

# =====================
# DB 초기화
# =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

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

# =====================
# 접근 제어 (로그인 필수)
# =====================
@app.before_request
def require_login():
    # static, robots, login 은 예외
    if request.path.startswith("/static"):
        return
    if request.path in ("/login", "/robots.txt"):
        return

    if not session.get("logged_in"):
        return redirect(url_for("login"))

@app.after_request
def add_noindex_headers(resp):
    resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return resp

# =====================
# 로그인 / 로그아웃
# =====================
@app.get("/login")
def login():
    return render_template("login.html")

@app.post("/login")
def login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    user = USERS.get(username)
    if user and user["password"] == password:
        session.clear()
        session["logged_in"] = True
        session["user"] = username
        session["character"] = user["role"]
        return redirect(url_for("send"))

    return render_template(
        "login.html",
        error="아이디 또는 비밀번호가 올바르지 않습니다."
    )

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =====================
# 라우트
# =====================

@app.get("/")
def home():
    return redirect(url_for("send"))

# 메시지 입력 페이지
@app.get("/send")
def send():
    return render_template(
        "send.html",
        character=session.get("character"),
        user=session.get("user")
    )

# 메시지 전송 처리
@app.post("/send")
def send_post():
    content = (request.form.get("content") or "").strip()
    content = " ".join(content.splitlines()).strip()

    if not content:
        return ("메시지가 비어있습니다.", 400)
    if len(content) > 240:
        return ("메시지는 240자 이하로 해주세요.", 400)

    db = get_db()
    db.execute(
        "INSERT INTO messages (sender, content, created_at) VALUES (?, ?, ?)",
        (
            session.get("character"),
            content,
            datetime.utcnow().isoformat(timespec="seconds") + "Z"
        )
    )
    db.commit()

    return redirect(url_for("log_page"))

# 로그 페이지
@app.get("/log")
def log_page():
    db = get_db()
    rows = db.execute(
        """
        SELECT sender, content, created_at
        FROM messages
        ORDER BY id ASC
        """
    ).fetchall()

    return render_template(
        "log.html",
        rows=rows,
        character=session.get("character"),
        user=session.get("user")
    )

# 갤러리 페이지
@app.get("/gallery")
def gallery():
    return render_template("gallery.html")

# =====================
# robots.txt
# =====================
@app.get("/robots.txt")
def robots():
    resp = make_response("User-agent: *\nDisallow: /\n", 200)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp

# =====================
# 실행
# =====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
