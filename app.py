from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
import sqlite3
import hashlib
import os
import time
from igdb import search_games, featured_games

app = Flask(__name__)
app.secret_key = "secret123"

DB = "database.db"

FEATURED_CACHE_TTL = 600
_featured_cache = {"at": 0.0, "payload": None}


def safe_next_path(value):
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value.startswith("/") or value.startswith("//"):
        return None
    return value


def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            display_name TEXT,
            bio TEXT,
            avatar TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---- Helper ----
def get_db():
    return sqlite3.connect(DB)


def get_community_trending(limit=8):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT game_name,
                   MAX(image) AS image,
                   COUNT(*) AS add_count
            FROM library
            GROUP BY game_name
            ORDER BY add_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        img = r[1] if r[1] else None
        out.append({"name": r[0], "image": img, "add_count": r[2]})
    return out


@app.context_processor
def inject_nav():
    uid = session.get("user_id")
    display_name = None
    if uid:
        with get_db() as conn:
            row = conn.execute(
                "SELECT username, display_name FROM users WHERE id=?",
                (uid,),
            ).fetchone()
        if row:
            display_name = (row[1] or "").strip() or row[0]
    return {
        "logged_in": bool(uid),
        "nav_display_name": display_name,
        "current_path": request.path,
    }


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---- Setup DB ----
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

# ---- Routes ----

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = hash_password(request.form["password"])
    next_path = safe_next_path(request.form.get("next"))

    with get_db() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()

    if user and user[2] == password:
        session["user_id"] = user[0]
        return redirect(next_path or "/dashboard")

    flash("Invalid username or password.", "error")
    nxt = request.form.get("next", "").strip()
    if nxt and safe_next_path(nxt):
        return redirect(url_for("login", next=nxt))
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password),
                )
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("That username is already taken.", "error")
            return redirect(url_for("signup_page"))

    return render_template("signup.html")
    
@app.route("/api/games")
def get_games():
    query = request.args.get("q", "")

    if not query:
        return jsonify([])
    games = search_games(query)
    return jsonify(games)


@app.route("/api/featured")
def api_featured():
    now = time.time()
    if (
        _featured_cache["payload"] is not None
        and now - _featured_cache["at"] < FEATURED_CACHE_TTL
    ):
        return jsonify(_featured_cache["payload"])

    community = get_community_trending(8)
    popular = featured_games(12)
    payload = {"community": community, "popular": popular}
    _featured_cache["at"] = now
    _featured_cache["payload"] = payload
    return jsonify(payload)


def _library_page():
    if "user_id" not in session:
        return redirect(url_for("login", next=url_for("library_page")))
    return render_template("dashboard.html")


@app.route("/dashboard")
def dashboard():
    return _library_page()


@app.route("/library")
def library_page():
    return _library_page()


with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_name TEXT,
            image TEXT,
            status TEXT,
            rating REAL,
            notes TEXT
        )
    """)
    _lib_cols = [r[1] for r in conn.execute("PRAGMA table_info(library)").fetchall()]
    if _lib_cols and "image" not in _lib_cols:
        conn.execute("ALTER TABLE library ADD COLUMN image TEXT")
    conn.commit()

@app.route("/api/add_game", methods=["POST"])
def add_game():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json

    print("ADD GAME DATA:", data) 
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO library (user_id, game_name, image, status, rating, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                data.get("name"),
                data.get("image"),
                data.get("status"),
                data.get("rating"),
                data.get("notes")
            ))
            conn.commit()

        _featured_cache["payload"] = None
        return jsonify({"success": True})

    except Exception as e:
        print("ADD GAME ERROR:", e)
        return jsonify({"error": "Server error"}), 500
    
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            display_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            avatar TEXT DEFAULT ''
        )
    """)
    
@app.route("/api/profile")
def get_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        conn = get_db()
        cur = conn.cursor()

        user = cur.execute("""
            SELECT username, display_name, bio, avatar
            FROM users
            WHERE id=?
        """, (session["user_id"],)).fetchone()

        conn.close()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "username": user[0] or "",
            "display_name": user[1] or "",
            "bio": user[2] or "",
            "avatar": user[3] or ""
        })

    except Exception as e:
        print("PROFILE ERROR:", e)
        return jsonify({"error": "Server error"}), 500
    
@app.route("/api/my_games")
def my_games():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    q = request.args.get("q", "").strip()
    with get_db() as conn:
        if q:
            pattern = f"%{q}%"
            games = conn.execute("""
                SELECT game_name, image, status, rating, notes
                FROM library
                WHERE user_id=? AND (
                    LOWER(game_name) LIKE LOWER(?)
                    OR LOWER(IFNULL(status, '')) LIKE LOWER(?)
                )
            """, (session["user_id"], pattern, pattern)).fetchall()
        else:
            games = conn.execute("""
                SELECT game_name, image, status, rating, notes
                FROM library
                WHERE user_id=?
            """, (session["user_id"],)).fetchall()

    return jsonify([
        {
            "name": g[0],
            "image": g[1],
            "status": g[2],
            "rating": g[3],
            "notes": g[4]
        }
        for g in games
    ])
    
@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json

    with get_db() as conn:
        conn.execute("""
            UPDATE users
            SET display_name=?, bio=?, avatar=?
            WHERE id=?
        """, (
            data.get("display_name", ""),
            data.get("bio", ""),
            data.get("avatar", ""),
            session["user_id"]
        ))
        conn.commit() 

    return jsonify({"success": True})


@app.route("/api/remove_game", methods=["POST"])
def remove_game():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json

    with get_db() as conn:
        conn.execute("""
            DELETE FROM library
            WHERE user_id=? AND game_name=?
        """, (session["user_id"], data.get("name")))
        conn.commit()

    _featured_cache["payload"] = None
    return jsonify({"success": True})

@app.route("/api/update_game", methods=["POST"])
def update_game():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json

    with get_db() as conn:
        conn.execute("""
            UPDATE library
            SET status=?, rating=?, notes=?
            WHERE user_id=? AND game_name=?
        """, (
            data.get("status"),
            data.get("rating"),
            data.get("notes"),
            session["user_id"],
            data.get("name")
        ))
        conn.commit()

    return jsonify({"success": True})


if __name__ == "__main__":
    # Default to 5050 so a stale/other Flask app on 5000 does not mask this instance.
    port = int(os.environ.get("QUESTLOG_PORT", "5050"))
    root = app.root_path
    style_path = os.path.join(root, "static", "style.css")
    style_hint = ""
    try:
        with open(style_path, encoding="utf-8") as f:
            head = f.read(80).replace("\n", " ").strip()
            style_hint = head[:72] + ("…" if len(head) > 72 else "")
    except OSError as e:
        style_hint = f"(could not read style.css: {e})"

    print("\n--- QuestLog ---")
    print(f"Serving from: {root}")
    print(f"Open: http://127.0.0.1:{port}/")
    print(f"style.css starts: {style_hint}")
    print("----------------\n")

    app.run(debug=True, port=port, use_reloader=True)