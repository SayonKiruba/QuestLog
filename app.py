from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
from igdb import search_games
import os

app = Flask(__name__)
app.secret_key = "secret123"

DB = "database.db"

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
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = hash_password(request.form["password"])

    with get_db() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()

    if user and user[2] == password:
        session["user_id"] = user[0]
        return redirect("/dashboard")
    else:
        return "Invalid login"

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    password = hash_password(request.form["password"])

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
        return redirect("/")
    except:
        return "Username already exists"
    
@app.route("/api/games")
def get_games():
    query = request.args.get("q", "")

    if not query:
        return []
    games = search_games(query)
    return games

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("dashboard.html")


with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_name TEXT,
            status TEXT,
            rating REAL,
            notes TEXT
        )
    """)
    
@app.route("/api/add_game", methods=["POST"])
def add_game():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

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

        return {"success": True}

    except Exception as e:
        print("ADD GAME ERROR:", e) 
        return {"error": "Server error"}, 500
    
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
        return {"error": "Not logged in"}, 401

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
            return {"error": "User not found"}, 404

        return {
            "username": user[0] or "",
            "display_name": user[1] or "",
            "bio": user[2] or "",
            "avatar": user[3] or ""
        }

    except Exception as e:
        print("PROFILE ERROR:", e)
        return {"error": "Server error"}, 500
    
@app.route("/api/my_games")
def my_games():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    with get_db() as conn:
        games = conn.execute("""
            SELECT game_name, image, status, rating, notes
            FROM library
            WHERE user_id=?
        """, (session["user_id"],)).fetchall()

    return [
        {
            "name": g[0],
            "image": g[1],
            "status": g[2],
            "rating": g[3],
            "notes": g[4]
        }
        for g in games
    ]
    
@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

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

    return {"success": True}


@app.route("/api/remove_game", methods=["POST"])
def remove_game():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    data = request.json

    with get_db() as conn:
        conn.execute("""
            DELETE FROM library
            WHERE user_id=? AND game_name=?
        """, (session["user_id"], data.get("name")))
        conn.commit()

    return {"success": True}

@app.route("/api/update_game", methods=["POST"])
def update_game():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

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

    return {"success": True}


if __name__ == "__main__":
    app.run(debug=True)