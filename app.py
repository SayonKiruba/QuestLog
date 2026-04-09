from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
import sqlite3
import hashlib
import os
import time
from igdb import search_games, featured_games

app = Flask(__name__)
app.secret_key = "secret123"

DB = "database.db"
FALLBACK_DB = os.path.join(os.environ.get("TEMP", os.getcwd()), "questlog_fallback.db")

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
    global DB
    try:
        with get_db() as conn:
            _apply_schema(conn)
            conn.commit()
    except sqlite3.OperationalError as e:
        if DB == FALLBACK_DB:
            raise
        print(f"Database init failed for {DB}: {e}. Falling back to {FALLBACK_DB}.")
        DB = FALLBACK_DB
        with get_db() as conn:
            _apply_schema(conn)
            conn.commit()

# ---- Helper ----
def get_db():
    return sqlite3.connect(DB, timeout=5)


def _apply_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            display_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0
        )
    """)
    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "display_name" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''")
    if "bio" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
    if "avatar" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT ''")
    if "is_admin" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

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
    lib_cols = [r[1] for r in conn.execute("PRAGMA table_info(library)").fetchall()]
    if "image" not in lib_cols:
        conn.execute("ALTER TABLE library ADD COLUMN image TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            igdb_id INTEGER,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            image TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            is_blacklisted INTEGER DEFAULT 0,
            created_by INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    admin_cols = [r[1] for r in conn.execute("PRAGMA table_info(admin_games)").fetchall()]
    if "igdb_id" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN igdb_id INTEGER")
    if "normalized_name" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN normalized_name TEXT NOT NULL DEFAULT ''")
    if "image" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN image TEXT DEFAULT ''")
    if "summary" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN summary TEXT DEFAULT ''")
    if "is_blacklisted" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN is_blacklisted INTEGER DEFAULT 0")
    if "created_by" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN created_by INTEGER")
    if "updated_at" not in admin_cols:
        conn.execute("ALTER TABLE admin_games ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

    conn.execute("""
        UPDATE admin_games
        SET normalized_name = LOWER(TRIM(name))
        WHERE IFNULL(normalized_name, '') = ''
    """)


def normalize_game_name(value):
    return " ".join((value or "").strip().lower().split())


def get_community_trending(limit=8):
    blacklist_ids, blacklist_names = get_blacklist_filters()
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
            (limit * 3,),
        ).fetchall()
    out = []
    for r in rows:
        if normalize_game_name(r[0]) in blacklist_names:
            continue
        img = r[1] if r[1] else None
        out.append({"name": r[0], "image": img, "add_count": r[2]})
        if len(out) >= limit:
            break
    return out


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, username, display_name, bio, avatar, IFNULL(is_admin, 0)
            FROM users
            WHERE id=?
            """,
            (uid,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2] or "",
        "bio": row[3] or "",
        "avatar": row[4] or "",
        "is_admin": bool(row[5]),
    }


def is_current_user_admin():
    user = current_user()
    return bool(user and user["is_admin"])


def admin_required_json():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    if not is_current_user_admin():
        return jsonify({"error": "Admin access required"}), 403
    return None


def get_blacklist_filters():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT igdb_id, normalized_name
            FROM admin_games
            WHERE is_blacklisted=1
            """
        ).fetchall()
    blacklist_ids = {r[0] for r in rows if r[0] is not None}
    blacklist_names = {r[1] for r in rows if r[1]}
    return blacklist_ids, blacklist_names


def get_admin_override_maps():
    rows = get_admin_catalog_rows(include_blacklisted=False)
    by_igdb_id = {}
    by_name = {}
    for row in rows:
        game = serialize_admin_game(row)
        if game["igdb_id"] is not None:
            by_igdb_id[game["igdb_id"]] = game
        by_name[game["normalized_name"]] = game
    return by_igdb_id, by_name


def is_game_blacklisted(game, blacklist_ids, blacklist_names):
    gid = game.get("id")
    if gid is not None and gid in blacklist_ids:
        return True
    return normalize_game_name(game.get("name")) in blacklist_names


def apply_admin_override(game, by_igdb_id, by_name):
    override = None
    gid = game.get("id")
    if gid is not None:
        override = by_igdb_id.get(gid)
    if not override:
        override = by_name.get(normalize_game_name(game.get("name")))
    if not override:
        return game

    merged = dict(game)
    merged["name"] = override["name"]
    if override["summary"]:
        merged["summary"] = override["summary"]
    if override["image"]:
        merged["cover"] = {"url": override["image"].replace("https://", "//")}
    merged["admin_game_id"] = override["id"]
    merged["is_overridden"] = True
    return merged


def serialize_admin_game(row):
    return {
        "id": row[0],
        "igdb_id": row[1],
        "name": row[2],
        "normalized_name": row[3],
        "image": row[4] or "",
        "summary": row[5] or "",
        "is_blacklisted": bool(row[6]),
        "created_by": row[7],
        "updated_at": row[8],
    }


def get_admin_catalog_rows(include_blacklisted=True):
    query = """
        SELECT id, igdb_id, name, normalized_name, image, summary, is_blacklisted, created_by, updated_at
        FROM admin_games
    """
    if not include_blacklisted:
        query += " WHERE is_blacklisted=0"
    query += " ORDER BY updated_at DESC, id DESC"
    with get_db() as conn:
        return conn.execute(query).fetchall()


def upsert_admin_game(name, image="", summary="", igdb_id=None, is_blacklisted=0, created_by=None):
    normalized_name = normalize_game_name(name)
    with get_db() as conn:
        existing = None
        if igdb_id is not None:
            existing = conn.execute(
                "SELECT id FROM admin_games WHERE igdb_id=?",
                (igdb_id,),
            ).fetchone()
        if not existing:
            existing = conn.execute(
                "SELECT id FROM admin_games WHERE normalized_name=?",
                (normalized_name,),
            ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE admin_games
                SET igdb_id=COALESCE(?, igdb_id),
                    name=?,
                    normalized_name=?,
                    image=?,
                    summary=?,
                    is_blacklisted=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    igdb_id,
                    name.strip(),
                    normalized_name,
                    image.strip(),
                    summary.strip(),
                    int(bool(is_blacklisted)),
                    existing[0],
                ),
            )
            game_id = existing[0]
        else:
            cur = conn.execute(
                """
                INSERT INTO admin_games (
                    igdb_id, name, normalized_name, image, summary, is_blacklisted, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    igdb_id,
                    name.strip(),
                    normalized_name,
                    image.strip(),
                    summary.strip(),
                    int(bool(is_blacklisted)),
                    created_by,
                ),
            )
            game_id = cur.lastrowid
        conn.commit()
    return game_id


@app.context_processor
def inject_nav():
    user = current_user()
    display_name = None
    if user:
        display_name = (user["display_name"] or "").strip() or user["username"]
    return {
        "logged_in": bool(user),
        "nav_display_name": display_name,
        "current_path": request.path,
        "nav_is_admin": bool(user and user["is_admin"]),
    }


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---- Setup DB ----
init_db()

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
        username = request.form["username"].strip()
        password = hash_password(request.form["password"])
        is_admin = 1 if request.form.get("is_admin") == "on" else 0

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                    (username, password, is_admin),
                )
                conn.commit()
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That username is already taken.", "error")
            return redirect(url_for("signup_page"))

    return render_template("signup.html")
    
@app.route("/api/games")
def get_games():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])
    blacklist_ids, blacklist_names = get_blacklist_filters()
    override_by_id, override_by_name = get_admin_override_maps()
    igdb_games = search_games(query)
    filtered_igdb = []
    for game in igdb_games:
        if is_game_blacklisted(game, blacklist_ids, blacklist_names):
            continue
        filtered_igdb.append(apply_admin_override(game, override_by_id, override_by_name))

    pattern = f"%{query}%"
    with get_db() as conn:
        admin_rows = conn.execute(
            """
            SELECT id, igdb_id, name, normalized_name, image, summary, is_blacklisted, created_by, updated_at
            FROM admin_games
            WHERE is_blacklisted=0 AND LOWER(name) LIKE LOWER(?)
            ORDER BY updated_at DESC, id DESC
            """,
            (pattern,),
        ).fetchall()

    existing_names = {normalize_game_name(g.get("name")) for g in filtered_igdb}
    existing_ids = {g.get("id") for g in filtered_igdb if g.get("id") is not None}
    extra_games = []
    for row in admin_rows:
        game = serialize_admin_game(row)
        if game["igdb_id"] is not None and game["igdb_id"] in existing_ids:
            continue
        if game["normalized_name"] in existing_names:
            continue
        payload = {
            "id": game["igdb_id"] if game["igdb_id"] is not None else f"local-{game['id']}",
            "name": game["name"],
            "summary": game["summary"],
            "is_local": True,
            "admin_game_id": game["id"],
        }
        if game["image"]:
            payload["cover"] = {"url": game["image"].replace("https://", "//")}
        extra_games.append(payload)

    return jsonify(extra_games + filtered_igdb)


@app.route("/api/featured")
def api_featured():
    now = time.time()
    if (
        _featured_cache["payload"] is not None
        and now - _featured_cache["at"] < FEATURED_CACHE_TTL
    ):
        return jsonify(_featured_cache["payload"])

    blacklist_ids, blacklist_names = get_blacklist_filters()
    override_by_id, override_by_name = get_admin_override_maps()
    community = get_community_trending(8)
    popular = []
    for game in featured_games(24):
        if is_game_blacklisted(game, blacklist_ids, blacklist_names):
            continue
        popular.append(apply_admin_override(game, override_by_id, override_by_name))
        if len(popular) >= 12:
            break
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


@app.route("/profiles")
def profiles_page():
    if "user_id" not in session:
        return redirect(url_for("login", next=url_for("profiles_page")))
    return render_template("profiles.html")


@app.route("/admin")
def admin_page():
    if "user_id" not in session:
        return redirect(url_for("login", next=url_for("admin_page")))
    if not is_current_user_admin():
        flash("Admin access required.", "error")
        return redirect(url_for("library_page"))
    return render_template("admin.html")


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
        user = current_user()
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "username": user["username"],
            "display_name": user["display_name"],
            "bio": user["bio"],
            "avatar": user["avatar"],
            "is_admin": user["is_admin"],
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


@app.route("/api/search_profiles")
def search_profiles():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    query = request.args.get("q", "").strip()
    
    if not query:
        return jsonify([])

    try:
        with get_db() as conn:
            pattern = f"%{query}%"
            profiles = conn.execute("""
                SELECT id, username, display_name, bio, avatar
                FROM users
                WHERE (LOWER(username) LIKE LOWER(?) OR LOWER(display_name) LIKE LOWER(?))
                LIMIT 16
            """, (pattern, pattern)).fetchall()

        result = []
        for p in profiles:
            user_id, username, display_name, bio, avatar = p
            # Count games for this user
            with get_db() as conn:
                game_count = conn.execute(
                    "SELECT COUNT(*) FROM library WHERE user_id=?",
                    (user_id,)
                ).fetchone()[0]
            
            result.append({
                "username": username,
                "display_name": display_name or "",
                "bio": bio or "",
                "avatar": avatar or "",
                "games_count": game_count
            })

        return jsonify(result)

    except Exception as e:
        print("SEARCH PROFILES ERROR:", e)
        return jsonify({"error": "Server error"}), 500


@app.route("/api/profiles/<username>")
def get_public_profile(username):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        with get_db() as conn:
            # Get profile info
            profile = conn.execute("""
                SELECT id, username, display_name, bio, avatar
                FROM users
                WHERE username=?
            """, (username,)).fetchone()

            if not profile:
                return jsonify({"error": "Profile not found"}), 404

            user_id = profile[0]
            
            # Get user's games
            games = conn.execute("""
                SELECT game_name, image, status, rating, notes
                FROM library
                WHERE user_id=?
                ORDER BY game_name
            """, (user_id,)).fetchall()

        return jsonify({
            "username": profile[1],
            "display_name": profile[2] or "",
            "bio": profile[3] or "",
            "avatar": profile[4] or "",
            "games": [
                {
                    "name": g[0],
                    "image": g[1],
                    "status": g[2],
                    "rating": g[3],
                    "notes": g[4]
                }
                for g in games
            ]
        })

    except Exception as e:
        print("GET PUBLIC PROFILE ERROR:", e)
        return jsonify({"error": "Server error"}), 500


@app.route("/api/admin/games")
def admin_games_list():
    denied = admin_required_json()
    if denied:
        return denied
    rows = get_admin_catalog_rows(include_blacklisted=True)
    return jsonify([serialize_admin_game(r) for r in rows])


@app.route("/api/admin/games", methods=["POST"])
def admin_create_game():
    denied = admin_required_json()
    if denied:
        return denied

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    game_id = upsert_admin_game(
        name=name,
        image=data.get("image", ""),
        summary=data.get("summary", ""),
        igdb_id=data.get("igdb_id"),
        is_blacklisted=data.get("is_blacklisted", False),
        created_by=session["user_id"],
    )
    _featured_cache["payload"] = None
    return jsonify({"success": True, "id": game_id})


@app.route("/api/admin/games/<int:game_id>", methods=["POST"])
def admin_update_game_entry(game_id):
    denied = admin_required_json()
    if denied:
        return denied

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM admin_games WHERE id=?",
            (game_id,),
        ).fetchone()
        if not exists:
            return jsonify({"error": "Game not found"}), 404
        conn.execute(
            """
            UPDATE admin_games
            SET igdb_id=?,
                name=?,
                normalized_name=?,
                image=?,
                summary=?,
                is_blacklisted=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data.get("igdb_id"),
                name,
                normalize_game_name(name),
                (data.get("image") or "").strip(),
                (data.get("summary") or "").strip(),
                int(bool(data.get("is_blacklisted"))),
                game_id,
            ),
        )
        conn.commit()
    _featured_cache["payload"] = None
    return jsonify({"success": True})


@app.route("/api/admin/games/<int:game_id>", methods=["DELETE"])
def admin_delete_game_entry(game_id):
    denied = admin_required_json()
    if denied:
        return denied

    with get_db() as conn:
        conn.execute("DELETE FROM admin_games WHERE id=?", (game_id,))
        conn.commit()
    _featured_cache["payload"] = None
    return jsonify({"success": True})


@app.route("/api/admin/blacklist", methods=["POST"])
def admin_blacklist_game():
    denied = admin_required_json()
    if denied:
        return denied

    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    game_id = upsert_admin_game(
        name=name,
        image=data.get("image", ""),
        summary=data.get("summary", ""),
        igdb_id=data.get("igdb_id"),
        is_blacklisted=True,
        created_by=session["user_id"],
    )
    _featured_cache["payload"] = None
    return jsonify({"success": True, "id": game_id})


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
