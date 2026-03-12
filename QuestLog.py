import os
import re
import sqlite3
import hashlib
import secrets
import tkinter as tk
from tkinter import ttk, messagebox

DB_PATH = os.path.join(os.path.dirname(__file__), "questlog.db")

STATUSES = ["Played", "Want to Play", "Currently Playing"]
GENRES = ["Action","Adventure","RPG","Shooter","Strategy","Simulation","Sports","Horror","Puzzle","Platformer","Open World"]
# Auth helpers (PBKDF2)
def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt, dk

def verify_password(password: str, salt: bytes, pw_hash: bytes) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return secrets.compare_digest(dk, pw_hash)

def clamp_rating(x: str) -> float | None:
    x = x.strip()
    if x == "":
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    if v < 0:
        v = 0.0
    if v > 10:
        v = 10.0
    return round(v, 1)
# Database
class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row

    def init(self):
        c = self.conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT DEFAULT '',
                accent TEXT DEFAULT '#7c3aed',
                avatar_style TEXT DEFAULT 'sigil',
                role TEXT NOT NULL CHECK(role IN ('user','admin')),
                salt BLOB NOT NULL,
                pw_hash BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                genre TEXT NOT NULL,
                description TEXT NOT NULL,
                db_rating REAL NOT NULL CHECK(db_rating >= 0 AND db_rating <= 10)
            );

            CREATE TABLE IF NOT EXISTS library (
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Played','Want to Play','Currently Playing')),
                user_rating REAL NULL CHECK(user_rating IS NULL OR (user_rating >= 0 AND user_rating <= 10)),
                notes TEXT DEFAULT '',
                PRIMARY KEY(user_id, game_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()
        self.seed_if_empty()
    
    def seed_if_empty(self):
        pass

    
    # ---- Users
    def get_user_by_username(self, username: str):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE lower(username)=lower(?)", (username.strip(),))
        return cur.fetchone()

    def create_user(self, username: str, password: str, role: str):
        username = username.strip()
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")
        if not re.match(r"^[A-Za-z0-9_]+$", username):
            raise ValueError("Username must be letters/numbers/underscore only.")
        salt, pw_hash = hash_password(password)
        display = username
        accent = "#7c3aed" if role == "admin" else "#06b6d4"
        avatar = "sigil" if role == "admin" else "orb"
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO users(username, display_name, bio, accent, avatar_style, role, salt, pw_hash)
               VALUES(?,?,?,?,?,?,?,?)""",
            (username, display, "", accent, avatar, role, salt, pw_hash),
        )
        self.conn.commit()
        return self.get_user_by_username(username)

    def update_profile(self, user_id: int, display_name: str, bio: str, accent: str, avatar_style: str):
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE users SET display_name=?, bio=?, accent=?, avatar_style=? WHERE id=?""",
            (display_name.strip() or "Player", bio or "", accent or "#7c3aed", avatar_style, user_id),
        )
        self.conn.commit()

    def search_profiles(self, q: str):
        q = q.strip().lower()
        cur = self.conn.cursor()
        if not q:
            cur.execute("SELECT id, username, display_name, bio, accent, avatar_style, role FROM users ORDER BY id DESC")
            return cur.fetchall()
        like = f"%{q}%"
        cur.execute(
            """SELECT id, username, display_name, bio, accent, avatar_style, role
               FROM users
               WHERE lower(username) LIKE ? OR lower(display_name) LIKE ? OR lower(bio) LIKE ?
               ORDER BY id DESC""",
            (like, like, like),
        )
        return cur.fetchall()

    # ---- Games
    def search_games(self, q: str):
        q = q.strip().lower()
        cur = self.conn.cursor()
        if not q:
            cur.execute("SELECT * FROM games ORDER BY id DESC")
            return cur.fetchall()
        like = f"%{q}%"
        cur.execute(
            """SELECT * FROM games
               WHERE lower(name) LIKE ? OR lower(genre) LIKE ? OR lower(description) LIKE ?
               ORDER BY id DESC""",
            (like, like, like),
        )
        return cur.fetchall()

    def get_game(self, game_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM games WHERE id=?", (game_id,))
        return cur.fetchone()

    def add_game(self, name: str, genre: str, description: str, db_rating: float):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO games(name, genre, description, db_rating) VALUES(?,?,?,?)",
            (name.strip(), genre.strip(), description.strip() or "(no description)", db_rating),
        )
        self.conn.commit()

    def update_game(self, game_id: int, name: str, genre: str, description: str, db_rating: float):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE games SET name=?, genre=?, description=?, db_rating=? WHERE id=?",
            (name.strip(), genre.strip(), description.strip() or "(no description)", db_rating, game_id),
        )
        self.conn.commit()

    # ---- Library
    def get_library_entry(self, user_id: int, game_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM library WHERE user_id=? AND game_id=?", (user_id, game_id))
        return cur.fetchone()

    def upsert_library_entry(self, user_id: int, game_id: int, status: str, user_rating: float | None, notes: str):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO library(user_id, game_id, status, user_rating, notes)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id, game_id) DO UPDATE SET
                 status=excluded.status,
                 user_rating=excluded.user_rating,
                 notes=excluded.notes
            """,
            (user_id, game_id, status, user_rating, notes or ""),
        )
        self.conn.commit()

    def remove_from_library(self, user_id: int, game_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM library WHERE user_id=? AND game_id=?", (user_id, game_id))
        self.conn.commit()

    def library_by_status(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute(
            """SELECT l.*, g.name, g.genre
               FROM library l
               JOIN games g ON g.id=l.game_id
               WHERE l.user_id=?
               ORDER BY g.name COLLATE NOCASE""",
            (user_id,),
        )
        rows = cur.fetchall()
        buckets = {s: [] for s in STATUSES}
        for r in rows:
            buckets[r["status"]].append(r)
        return buckets

    def library_for_user(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute(
            """SELECT l.*, g.name, g.genre
               FROM library l
               JOIN games g ON g.id=l.game_id
               WHERE l.user_id=?
               ORDER BY g.name COLLATE NOCASE""",
            (user_id,),
        )
        return cur.fetchall()

    # ---- Comments (optional)
    def add_comment(self, game_id: int, user_id: int, text: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO comments(game_id, user_id, text) VALUES(?,?,?)",
            (game_id, user_id, text.strip()),
        )
        self.conn.commit()

    def get_comments(self, game_id: int, limit: int = 10):
        cur = self.conn.cursor()
        cur.execute(
            """SELECT c.text, c.created_at, u.display_name, u.username
               FROM comments c
               JOIN users u ON u.id=c.user_id
               WHERE c.game_id=?
               ORDER BY c.id DESC
               LIMIT ?""",
            (game_id, limit),
        )
        return cur.fetchall()

# UI
class QuestLogApp(tk.Tk):
    def __init__(self, db: DB):
        super().__init__()
        self.db = db
        self.title("QuestLog (Prototype)")
        self.geometry("980x620")
        self.minsize(920, 560)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # ----- Custom Theme Colors -----
        self.colors = {
            "bg_dark": "#14110F",
            "bg_mid": "#34312D",
            "bg_light": "#F3F3F4",
            "text_light": "#F3F3F4",
            "text_dark": "#14110F",
            "accent": "#D9C5B2",
            "muted": "#7E7F83"
        }
        self.dark_mode = True
        self.apply_theme()


        self.user = None  # sqlite Row

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (AuthFrame, MainFrame):
            frame = F(parent=container, app=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("AuthFrame")


    def apply_theme(self):
        c = self.colors
        if self.dark_mode:
            bg = c["bg_dark"]
            fg = c["text_light"]
            panel = c["bg_mid"]
        else:
            bg = c["bg_light"]
            fg = c["text_dark"]
            panel = "#FFFFFF"

        self.configure(bg=bg)

        style = self.style
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TNotebook", background=bg)
        style.configure("TButton", background=c["accent"], foreground=c["text_dark"], padding=6)
        style.configure("TEntry", fieldbackground=panel, foreground=fg)

    def show(self, name: str):
        self.frames[name].tkraise()
        if name == "MainFrame":
            self.frames[name].refresh_all()

    def login(self, user_row):
        self.user = user_row
        self.show("MainFrame")

    def logout(self):
        self.user = None
        self.show("AuthFrame")

class AuthFrame(ttk.Frame):
    def __init__(self, parent, app: QuestLogApp):
        super().__init__(parent)
        self.app = app

        self.mode = tk.StringVar(value="login")
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.admin_signup = tk.BooleanVar(value=False)

        wrap = ttk.Frame(self, padding=24)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        title = ttk.Label(wrap, text="QuestLog", font=("Segoe UI", 22, "bold"))
        subtitle = ttk.Label(wrap, text="rate • tag • track", foreground="#666")
        title.grid(row=0, column=0, columnspan=2, pady=(0, 2))
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 18))

        modebar = ttk.Frame(wrap)
        modebar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.btn_login = ttk.Button(modebar, text="Log in", command=lambda: self.set_mode("login"))
        self.btn_signup = ttk.Button(modebar, text="Sign up", command=lambda: self.set_mode("signup"))
        self.btn_login.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.btn_signup.pack(side="left", expand=True, fill="x")

        ttk.Label(wrap, text="Username").grid(row=3, column=0, sticky="w")
        ttk.Entry(wrap, textvariable=self.username, width=32).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(wrap, text="Password").grid(row=5, column=0, sticky="w")
        ttk.Entry(wrap, textvariable=self.password, show="•", width=32).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.admin_row = ttk.Frame(wrap)
        self.admin_row.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Checkbutton(self.admin_row, text="Admin (checkbox on sign up)", variable=self.admin_signup).pack(anchor="w")

        self.action_btn = ttk.Button(wrap, text="Log in", command=self.submit)
        self.action_btn.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        hint = ttk.Label(
            wrap,
            text="Prototype accounts: admin/admin and player/player\nNo purchases • No 2FA • Local SQLite DB",
            foreground="#666",
            justify="center",
        )
        hint.grid(row=9, column=0, columnspan=2)

        for i in range(2):
            wrap.columnconfigure(i, weight=1)

        self.set_mode("login")

    def set_mode(self, mode: str):
        self.mode.set(mode)
        self.action_btn.configure(text="Log in" if mode == "login" else "Create account")
        if mode == "signup":
            self.admin_row.grid()
        else:
            self.admin_row.grid_remove()

    def submit(self):
        u = self.username.get().strip()
        p = self.password.get()

        if self.mode.get() == "login":
            row = self.app.db.get_user_by_username(u)
            if not row:
                messagebox.showerror("Login failed", "Invalid username or password.")
                return
            if not verify_password(p, row["salt"], row["pw_hash"]):
                messagebox.showerror("Login failed", "Invalid username or password.")
                return
            self.app.login(row)
            return

        # signup
        role = "admin" if self.admin_signup.get() else "user"
        try:
            new_user = self.app.db.create_user(u, p, role)
        except sqlite3.IntegrityError:
            messagebox.showerror("Sign up failed", "That username is taken.")
            return
        except ValueError as e:
            messagebox.showerror("Sign up failed", str(e))
            return

        self.app.login(new_user)

class MainFrame(ttk.Frame):
    def __init__(self, parent, app: QuestLogApp):
        super().__init__(parent)
        self.app = app

        # Header
        header = ttk.Frame(self, padding=(14, 12))
        header.pack(fill="x")

        self.lbl_brand = ttk.Label(header, text="QuestLog", font=("Segoe UI", 16, "bold"))
        self.lbl_brand.pack(side="left")

        ttk.Label(header, text="   Search games (mandatory):").pack(side="left")
        self.game_search = tk.StringVar()
        ent = ttk.Entry(header, textvariable=self.game_search, width=42)
        ent.pack(side="left", padx=(6, 8))
        ent.bind("<KeyRelease>", lambda e: self.refresh_games())

        self.user_badge = ttk.Label(header, text="")
        self.user_badge.pack(side="right")

        ttk.Button(header, text="Log out", command=self.app.logout).pack(side="right", padx=(0, 10))
        ttk.Button(header, text="Toggle Theme", command=self.toggle_theme).pack(side="right", padx=6)

        # Tabs
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tab_games = ttk.Frame(self.tabs, padding=12)
        self.tab_profile = ttk.Frame(self.tabs, padding=12)
        self.tab_profiles = ttk.Frame(self.tabs, padding=12)
        self.tab_admin = ttk.Frame(self.tabs, padding=12)

        self.tabs.add(self.tab_games, text="Games")
        self.tabs.add(self.tab_profile, text="My Profile")
        self.tabs.add(self.tab_profiles, text="Profiles (extra)")
        # Admin tab added conditionally in refresh_all

        # Build tab contents
        self._build_games_tab()
        self._build_profile_tab()
        self._build_profiles_tab()
        self._build_admin_tab()


    def toggle_theme(self):
        self.app.dark_mode = not self.app.dark_mode
        self.app.apply_theme()

    # --------- Tab builders
    def _build_games_tab(self):
        left = ttk.Frame(self.tab_games)
        right = ttk.Frame(self.tab_games)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Games (from DB)", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(left, text="Select a game to view details, rate, tag, and comment.", foreground="#666").pack(anchor="w", pady=(0, 8))

        self.games_list = tk.Listbox(left, height=22)
        self.games_list.pack(fill="both", expand=True)
        self.games_list.bind("<<ListboxSelect>>", lambda e: self.on_select_game())

        # Right details
        ttk.Label(right, text="Details", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.details = tk.Text(right, height=8, wrap="word")
        self.details.pack(fill="x", pady=(6, 10))
        self.details.configure(state="disabled")

        form = ttk.LabelFrame(right, text="Add to your profile", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Status").grid(row=0, column=0, sticky="w")
        self.sel_status = tk.StringVar(value=STATUSES[1])
        ttk.Combobox(form, values=STATUSES, textvariable=self.sel_status, state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Your rating (0–10)").grid(row=0, column=1, sticky="w")
        self.ent_user_rating = tk.StringVar()
        ttk.Entry(form, textvariable=self.ent_user_rating).grid(row=1, column=1, sticky="ew")

        ttk.Label(form, text="Notes (extra)").grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.ent_notes = tk.Text(form, height=4, wrap="word")
        self.ent_notes.grid(row=3, column=0, columnspan=2, sticky="ew")

        btnrow = ttk.Frame(form)
        btnrow.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(btnrow, text="Save to profile", command=self.save_profile_entry).pack(side="left")
        ttk.Button(btnrow, text="Remove", command=self.remove_profile_entry).pack(side="left", padx=6)

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        # Comments (optional)
        comments = ttk.LabelFrame(right, text="Comments (optional)", padding=10)
        comments.pack(fill="both", expand=True)

        self.comments_box = tk.Listbox(comments, height=8)
        self.comments_box.pack(fill="both", expand=True)

        addrow = ttk.Frame(comments)
        addrow.pack(fill="x", pady=(8, 0))
        self.ent_comment = tk.StringVar()
        ttk.Entry(addrow, textvariable=self.ent_comment).pack(side="left", fill="x", expand=True)
        ttk.Button(addrow, text="Post", command=self.post_comment).pack(side="left", padx=(8, 0))

    def _build_profile_tab(self):
        top = ttk.Frame(self.tab_profile)
        top.pack(fill="x")

        self.profile_title = ttk.Label(top, text="", font=("Segoe UI", 12, "bold"))
        self.profile_title.pack(side="left")

        ttk.Button(top, text="Customize (extra)", command=self.open_customize).pack(side="right")

        self.profile_bio = ttk.Label(self.tab_profile, text="", foreground="#444", wraplength=820)
        self.profile_bio.pack(anchor="w", pady=(6, 10))

        self.library_tree = ttk.Treeview(
            self.tab_profile,
            columns=("status", "your_rating", "genre"),
            show="headings",
            height=16,
        )
        for col, label, w in [
            ("status", "Status", 160),
            ("your_rating", "Your Rating", 110),
            ("genre", "Genre", 180),
        ]:
            self.library_tree.heading(col, text=label)
            self.library_tree.column(col, width=w, stretch=True)
        self.library_tree.pack(fill="both", expand=True)

    def _build_profiles_tab(self):
        top = ttk.Frame(self.tab_profiles)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Profile search (extra)", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(top, text="   Search:").pack(side="left", padx=(14, 0))
        self.profile_search = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.profile_search, width=38)
        ent.pack(side="left", padx=(6, 0))
        ent.bind("<KeyRelease>", lambda e: self.refresh_profiles())

        body = ttk.Frame(self.tab_profiles)
        body.pack(fill="both", expand=True)

        self.profiles_list = tk.Listbox(body, height=18)
        self.profiles_list.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.profiles_list.bind("<<ListboxSelect>>", lambda e: self.on_select_profile())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self.other_profile_label = ttk.Label(right, text="Select a profile", font=("Segoe UI", 11, "bold"))
        self.other_profile_label.pack(anchor="w")
        self.other_profile_bio = ttk.Label(right, text="", foreground="#444", wraplength=430)
        self.other_profile_bio.pack(anchor="w", pady=(4, 8))

        self.other_library = tk.Listbox(right, height=18)
        self.other_library.pack(fill="both", expand=True)

    def _build_admin_tab(self):
        ttk.Label(self.tab_admin, text="Admin DB", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(self.tab_admin, text="Admins can add and edit games in the database.", foreground="#666").pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self.tab_admin)
        body.pack(fill="both", expand=True)

        self.admin_games = tk.Listbox(body, height=20)
        self.admin_games.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.admin_games.bind("<<ListboxSelect>>", lambda e: self.load_admin_selected())

        editor = ttk.LabelFrame(body, text="Add / Edit game", padding=10)
        editor.pack(side="left", fill="both", expand=True)

        self.adm_game_id = None
        self.adm_name = tk.StringVar()
        self.adm_genre = tk.StringVar()
        self.adm_rating = tk.StringVar()
        self.adm_desc = tk.Text(editor, height=8, wrap="word")

        ttk.Label(editor, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.adm_name).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(editor, text="Genre").grid(row=0, column=1, sticky="w")
        ttk.Combobox(editor, textvariable=self.adm_genre, values=GENRES, state="readonly").grid(row=1, column=1, sticky="ew")

        ttk.Label(editor, text="DB rating (0–10)").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(editor, textvariable=self.adm_rating).grid(row=3, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(editor, text="Description").grid(row=2, column=1, sticky="w", pady=(8, 0))
        # place description below across columns
        self.adm_desc.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(6, 0))

        btnrow = ttk.Frame(editor)
        btnrow.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(btnrow, text="New", command=self.admin_new).pack(side="left")
        ttk.Button(btnrow, text="Save", command=self.admin_save).pack(side="left", padx=6)

        editor.columnconfigure(0, weight=1)
        editor.columnconfigure(1, weight=1)
        editor.rowconfigure(4, weight=1)

    # --------- Refresh
    def refresh_all(self):
        u = self.app.user
        self.user_badge.configure(text=f"{u['display_name']}   (@{u['username']})   •   {u['role'].upper()}")
        # show/hide admin tab
        has_admin = any(self.tabs.tab(i, "text") == "Admin DB" for i in range(self.tabs.index("end")))
        if u["role"] == "admin":
            if not has_admin:
                self.tabs.add(self.tab_admin, text="Admin DB")
        else:
            if has_admin:
                # remove by searching index
                for i in range(self.tabs.index("end")):
                    if self.tabs.tab(i, "text") == "Admin DB":
                        self.tabs.forget(i)
                        break

        self.refresh_games()
        self.refresh_profile()
        self.refresh_profiles()
        if u["role"] == "admin":
            self.refresh_admin()

    def refresh_games(self):
        self.games = self.app.db.search_games(self.game_search.get())
        self.games_list.delete(0, tk.END)
        for g in self.games:
            self.games_list.insert(tk.END, f"{g['name']}  •  {g['genre']}  •  DB★ {g['db_rating']:.1f}")
        self.clear_game_details()

    def refresh_profile(self):
        u = self.app.db.get_user_by_username(self.app.user["username"])
        self.app.user = u  # refresh row
        self.profile_title.configure(text=f"My Profile — {u['display_name']}")
        bio = u["bio"] if u["bio"] else "(no bio yet)"
        self.profile_bio.configure(text=f"Bio: {bio}")

        self.library_tree.delete(*self.library_tree.get_children())
        rows = self.app.db.library_for_user(u["id"])
        for r in rows:
            yr = "" if r["user_rating"] is None else f"{r['user_rating']:.1f}"
            self.library_tree.insert("", tk.END, values=(r["status"], yr, r["genre"]), text=r["name"])

        # (Treeview doesn't show item text in headings-only mode; so add name into status column via formatting)
        # Simpler: rebuild with name in first column? We'll keep minimal: show in status column as "Name — Status".
        self.library_tree.delete(*self.library_tree.get_children())
        for r in rows:
            yr = "" if r["user_rating"] is None else f"{r['user_rating']:.1f}"
            self.library_tree.insert("", tk.END, values=(f"{r['name']} — {r['status']}", yr, r["genre"]))

    def refresh_profiles(self):
        self.profiles = self.app.db.search_profiles(self.profile_search.get())
        self.profiles_list.delete(0, tk.END)
        for p in self.profiles:
            self.profiles_list.insert(tk.END, f"{p['display_name']} (@{p['username']}) • {p['role']}")

        self.other_profile_label.configure(text="Select a profile")
        self.other_profile_bio.configure(text="")
        self.other_library.delete(0, tk.END)

    def refresh_admin(self):
        self.admin_games_data = self.app.db.search_games("")
        self.admin_games.delete(0, tk.END)
        for g in self.admin_games_data:
            self.admin_games.insert(tk.END, f"{g['name']} • {g['genre']} • DB★ {g['db_rating']:.1f}")
        self.admin_new()

    # --------- Games detail actions
    def clear_game_details(self):
        self.selected_game_id = None
        self.details.configure(state="normal")
        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, "Select a game to view details.\n")
        self.details.configure(state="disabled")

        self.sel_status.set(STATUSES[1])
        self.ent_user_rating.set("")
        self.ent_notes.delete("1.0", tk.END)

        self.comments_box.delete(0, tk.END)

    def on_select_game(self):
        idx = self.games_list.curselection()
        if not idx:
            return
        g = self.games[idx[0]]
        self.selected_game_id = g["id"]

        # show details
        self.details.configure(state="normal")
        self.details.delete("1.0", tk.END)
        self.details.insert(
            tk.END,
            f"{g['name']}\nGenre: {g['genre']}\nDB rating: {g['db_rating']:.1f}\n\n{g['description']}\n",
        )
        self.details.configure(state="disabled")

        # load library entry (if exists)
        u = self.app.user
        entry = self.app.db.get_library_entry(u["id"], g["id"])
        if entry:
            self.sel_status.set(entry["status"])
            self.ent_user_rating.set("" if entry["user_rating"] is None else f"{entry['user_rating']:.1f}")
            self.ent_notes.delete("1.0", tk.END)
            self.ent_notes.insert(tk.END, entry["notes"] or "")
        else:
            self.sel_status.set(STATUSES[1])
            self.ent_user_rating.set("")
            self.ent_notes.delete("1.0", tk.END)

        self.load_comments()

    def save_profile_entry(self):
        if not self.selected_game_id:
            messagebox.showinfo("No game selected", "Select a game first.")
            return
        status = self.sel_status.get()
        if status not in STATUSES:
            messagebox.showerror("Invalid status", "Pick a valid status.")
            return
        ur = clamp_rating(self.ent_user_rating.get())
        if self.ent_user_rating.get().strip() != "" and ur is None:
            messagebox.showerror("Invalid rating", "Your rating must be a number between 0 and 10.")
            return
        notes = self.ent_notes.get("1.0", tk.END).strip()
        self.app.db.upsert_library_entry(self.app.user["id"], self.selected_game_id, status, ur, notes)
        self.refresh_profile()
        messagebox.showinfo("Saved", "Saved to your profile.")

    def remove_profile_entry(self):
        if not self.selected_game_id:
            messagebox.showinfo("No game selected", "Select a game first.")
            return
        self.app.db.remove_from_library(self.app.user["id"], self.selected_game_id)
        self.refresh_profile()
        messagebox.showinfo("Removed", "Removed from your profile.")

    def post_comment(self):
        if not self.selected_game_id:
            messagebox.showinfo("No game selected", "Select a game first.")
            return
        text = self.ent_comment.get().strip()
        if not text:
            return
        self.app.db.add_comment(self.selected_game_id, self.app.user["id"], text)
        self.ent_comment.set("")
        self.load_comments()

    def load_comments(self):
        self.comments_box.delete(0, tk.END)
        if not self.selected_game_id:
            return
        rows = self.app.db.get_comments(self.selected_game_id, limit=10)
        for r in rows:
            self.comments_box.insert(tk.END, f"{r['display_name']} (@{r['username']}): {r['text']}   [{r['created_at']}]")

    # --------- Profile customization (extra)
    def open_customize(self):
        u = self.app.user
        win = tk.Toplevel(self)
        win.title("Profile customization (extra)")
        win.geometry("520x420")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=14)
        frm.pack(fill="both", expand=True)

        display = tk.StringVar(value=u["display_name"])
        bio = tk.StringVar(value=u["bio"] or "")
        accent = tk.StringVar(value=u["accent"] or "#7c3aed")
        avatar = tk.StringVar(value=u["avatar_style"] or "sigil")

        ttk.Label(frm, text="Display name").pack(anchor="w")
        ttk.Entry(frm, textvariable=display).pack(fill="x", pady=(0, 10))

        ttk.Label(frm, text="Bio").pack(anchor="w")
        bio_txt = tk.Text(frm, height=5, wrap="word")
        bio_txt.pack(fill="x", pady=(0, 10))
        bio_txt.insert(tk.END, bio.get())

        ttk.Label(frm, text="Accent (hex color)").pack(anchor="w")
        ttk.Entry(frm, textvariable=accent).pack(fill="x", pady=(0, 10))

        ttk.Label(frm, text="Avatar style").pack(anchor="w")
        ttk.Combobox(frm, textvariable=avatar, values=["orb", "sigil"], state="readonly").pack(fill="x", pady=(0, 16))

        def save():
            b = bio_txt.get("1.0", tk.END).strip()
            a = accent.get().strip() or "#7c3aed"
            if not re.match(r"^#[0-9a-fA-F]{6}$", a):
                messagebox.showerror("Invalid accent", "Accent must look like #RRGGBB (e.g., #7c3aed).")
                return
            self.app.db.update_profile(u["id"], display.get(), b, a, avatar.get())
            # reload current user row
            self.app.user = self.app.db.get_user_by_username(self.app.user["username"])
            self.refresh_all()
            win.destroy()

        ttk.Button(frm, text="Save", command=save).pack(anchor="e")

    # --------- Profiles (extra)
    def on_select_profile(self):
        idx = self.profiles_list.curselection()
        if not idx:
            return
        p = self.profiles[idx[0]]
        self.other_profile_label.configure(text=f"{p['display_name']} (@{p['username']}) • {p['role']}")
        self.other_profile_bio.configure(text=(p["bio"] if p["bio"] else "(no bio)"))

        rows = self.app.db.library_for_user(p["id"])
        self.other_library.delete(0, tk.END)
        if not rows:
            self.other_library.insert(tk.END, "(no games added)")
            return
        for r in rows[:20]:
            yr = "" if r["user_rating"] is None else f"★{r['user_rating']:.1f}"
            self.other_library.insert(tk.END, f"{r['name']} • {r['status']} {yr}")

    # --------- Admin DB
    def admin_new(self):
        self.adm_game_id = None
        self.adm_name.set("")
        self.adm_genre.set("")
        self.adm_rating.set("")
        self.adm_desc.delete("1.0", tk.END)

    def load_admin_selected(self):
        idx = self.admin_games.curselection()
        if not idx:
            return
        g = self.admin_games_data[idx[0]]
        self.adm_game_id = g["id"]
        self.adm_name.set(g["name"])
        self.adm_genre.set(g["genre"])
        self.adm_rating.set(f"{g['db_rating']:.1f}")
        self.adm_desc.delete("1.0", tk.END)
        self.adm_desc.insert(tk.END, g["description"])

    def admin_save(self):
        if self.app.user["role"] != "admin":
            messagebox.showerror("Not allowed", "Only admins can edit the game database.")
            return

        name = self.adm_name.get().strip()
        genre = self.adm_genre.get().strip()
        desc = self.adm_desc.get("1.0", tk.END).strip()
        r = clamp_rating(self.adm_rating.get())
        if not name:
            messagebox.showerror("Missing field", "Name is required.")
            return
        if not genre:
            messagebox.showerror("Missing field", "Genre is required.")
            return
        if r is None:
            messagebox.showerror("Invalid rating", "DB rating must be a number between 0 and 10.")
            return
        if not desc:
            desc = "(no description)"

        if self.adm_game_id is None:
            self.app.db.add_game(name, genre, desc, r)
            messagebox.showinfo("Added", "Added game to DB.")
        else:
            self.app.db.update_game(self.adm_game_id, name, genre, desc, r)
            messagebox.showinfo("Saved", "Updated DB entry.")

        # refresh everything (games list uses DB)
        self.refresh_games()
        self.refresh_admin()

def main():
    db = DB(DB_PATH)
    db.init()
    app = QuestLogApp(db)
    app.mainloop()

if __name__ == "__main__":
    main()