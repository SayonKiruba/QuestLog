import unittest
import sqlite3
import tempfile
import os
from unittest.mock import patch
import app

# Searching Profiles.

class TestApp(unittest.TestCase):

    def setUp(self):
        # Create test client
        self.app = app.app.test_client()
        self.app.testing = True

        # Use test database
        fd, path = tempfile.mkstemp(prefix="questlog_test_", suffix=".db")
        os.close(fd)
        app.DB = path
        app.init_db()

    def tearDown(self):
        if os.path.exists(app.DB):
            try:
                os.remove(app.DB)
            except PermissionError:
                pass


    def test_hash_password(self):
        hashed = app.hash_password("password")
        self.assertNotEqual(hashed, "password")
        self.assertEqual(hashed, app.hash_password("password"))

    def test_signup(self):
        response = self.app.post("/signup", data={
            "username": "testuser",
            "password": "123"
        })
        self.assertEqual(response.status_code, 302)

    def test_signup_admin_checkbox(self):
        self.app.post("/signup", data={
            "username": "adminuser",
            "password": "123",
            "is_admin": "on"
        })

        conn = sqlite3.connect(app.DB)
        row = conn.execute(
            "SELECT is_admin FROM users WHERE username=?",
            ("adminuser",)
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_login_success(self):
        conn = sqlite3.connect(app.DB)
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("testuser", app.hash_password("123"))
        )
        conn.commit()
        conn.close()

        response = self.app.post("/login", data={
            "username": "testuser",
            "password": "123"
        })

        self.assertEqual(response.status_code, 302)

    def test_login_fail(self):
        response = self.app.post("/login", data={
            "username": "wrong",
            "password": "wrong"
        }, follow_redirects=True)

        self.assertIn(b"Invalid username or password", response.data)

    def test_dashboard_requires_login(self):
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.app.get("/api/profile")
        self.assertEqual(response.status_code, 401)

    def test_admin_route_requires_admin(self):
        conn = sqlite3.connect(app.DB)
        conn.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            ("testuser", app.hash_password("123"), 0)
        )
        conn.commit()
        conn.close()

        with self.app.session_transaction() as sess:
            sess["user_id"] = 1

        response = self.app.get("/api/admin/games")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_game(self):
        conn = sqlite3.connect(app.DB)
        conn.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            ("admin", app.hash_password("123"), 1)
        )
        conn.commit()
        conn.close()

        with self.app.session_transaction() as sess:
            sess["user_id"] = 1

        response = self.app.post("/api/admin/games", json={
            "name": "School Project Game",
            "image": "https://example.com/cover.png",
            "summary": "Test summary"
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

    @patch("app.search_games")
    def test_admin_override_updates_existing_igdb_game(self, mock_search_games):
        mock_search_games.return_value = [{
            "id": 321,
            "name": "Original Game",
            "summary": "Original summary",
            "cover": {"url": "//images.igdb.com/igdb/image/upload/t_thumb/original.jpg"},
        }]

        conn = sqlite3.connect(app.DB)
        conn.execute(
            """
            INSERT INTO admin_games (igdb_id, name, normalized_name, image, summary, is_blacklisted)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                321,
                "Edited Game",
                "edited game",
                "https://example.com/override.png",
                "Overridden summary",
            ),
        )
        conn.commit()
        conn.close()

        response = self.app.get("/api/games?q=Original")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], 321)
        self.assertEqual(data[0]["name"], "Edited Game")
        self.assertEqual(data[0]["summary"], "Overridden summary")
        self.assertEqual(data[0]["cover"]["url"], "//example.com/override.png")

    @patch("app.search_games")
    def test_admin_blacklist_hides_existing_igdb_game(self, mock_search_games):
        mock_search_games.return_value = [{
            "id": 654,
            "name": "Blacklist Me",
            "summary": "Should not appear",
        }]

        conn = sqlite3.connect(app.DB)
        conn.execute(
            """
            INSERT INTO admin_games (igdb_id, name, normalized_name, image, summary, is_blacklisted)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                654,
                "Blacklist Me",
                "blacklist me",
                "",
                "",
            ),
        )
        conn.commit()
        conn.close()

        response = self.app.get("/api/games?q=Blacklist")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_search_profiles(self):
        conn = sqlite3.connect(app.DB)
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("testuser", app.hash_password("123"))
        )
        conn.commit()
        conn.close()

        with self.app.session_transaction() as sess:
            sess["user_id"] = 1

        response = self.app.get("/api/search_profiles?q=test")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
