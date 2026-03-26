import unittest
import sqlite3
import app


class TestApp(unittest.TestCase):

    def setUp(self):
        # Create test client
        self.app = app.app.test_client()
        self.app.testing = True

        # Use test database
        app.DB = "test.db"

        conn = sqlite3.connect(app.DB)
        cur = conn.cursor()

        # Create users table
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

        # Create library table
        cur.execute("""
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

        conn.commit()
        conn.close()

    def tearDown(self):
        import os
        if os.path.exists("test.db"):
            os.remove("test.db")

    # ----------------------
    # BASIC TESTS
    # ----------------------

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
        })

        self.assertIn(b"Invalid login", response.data)

    def test_dashboard_requires_login(self):
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 302)

    def test_profile_requires_login(self):
        response = self.app.get("/api/profile")
        self.assertEqual(response.status_code, 401)

    def test_search_profiles(self):
        """
        This test is written BEFORE the feature exists.
        It should FAIL (RED) because /api/search_profiles is not implemented yet.
        """

        response = self.app.get("/api/search_profiles?q=test")

        # Expect success (but will fail for now)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # Expect list of profiles
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()