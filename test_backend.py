"""
Backend Unit and Integration Test Suite.
Uses Python's standard unittest module to rigorously verify:
- Database connectivity & schema
- Password hashing and verification (PBKDF2)
- User registration and login flow
- FIFO Queue operations
- Min-Heap Priority Queue ordering (Emergency > High > Medium > Low)
- Resource multi-attribute search
- Grievance creation and status workflow
- Sorting algorithms
"""

import os
import sys
import unittest
import sqlite3
import hashlib
import time
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
import database
import server
from data_structures import (
    GrievanceQueue,
    GrievancePriorityQueue,
    search_resources,
    search_grievances,
    sort_grievances_by_priority,
    sort_grievances_by_date,
    sort_grievances_by_status
)


class CapturedAPIHandler(server.VillageAppHandler):
    """Run API routes directly and retain their JSON response for assertions."""

    def get_current_user(self):
        if hasattr(self, "current_user"):
            return self.current_user
        token = self.get_session_token()
        session = database.get_session(token) if token else None
        if session:
            return database.get_user_by_id(session["user_id"])
        return None

    def get_session_token(self):
        return getattr(self, "session_token", "")

    def send_json(self, data, status=200, set_cookies=None):
        self.response = {"data": data, "status": status, "cookies": set_cookies or []}

    def send_error_json(self, message, status=400, details=None):
        self.response = {
            "data": {"success": False, "error": message, "status": status},
            "status": status,
            "cookies": [],
        }


class TestVillageSystem(unittest.TestCase):
    """Main unit test suite for the Village Resource & Grievance System."""

    @classmethod
    def setUpClass(cls):
        """Ensure database is seeded prior to test runs."""
        from setup_database import init_database
        init_database()

    # =================================================================
    # 1. DATABASE & PASSWORD SECURITY TESTS
    # =================================================================

    def test_database_connection_and_tables(self):
        """Verify SQLite database exists and contains all 6 required tables."""
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]

        expected_tables = ["users", "departments", "resources", "grievances", "announcements", "grievance_updates"]
        for table in expected_tables:
            self.assertIn(table, tables, f"Expected table '{table}' not found in database.")
        user_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(users)")}
        self.assertIn("username", user_columns)
        conn.close()

    def test_password_hashing_and_verification(self):
        """Test PBKDF2-HMAC-SHA256 password hashing security."""
        raw_password = "SuperSecretPassword123!"
        hashed = database.hash_password(raw_password)

        # Ensure not stored in plain text
        self.assertNotEqual(raw_password, hashed)
        self.assertIn("$", hashed)

        # Verification with correct password
        self.assertTrue(database.verify_password(raw_password, hashed))

        # Verification failure with incorrect password
        self.assertFalse(database.verify_password("WrongPassword999", hashed))

        legacy_salt = "legacy-salt"
        legacy_hash = hashlib.pbkdf2_hmac(
            "sha256", raw_password.encode("utf-8"), legacy_salt.encode("utf-8"), 100_000
        ).hex()
        self.assertTrue(database.verify_password(raw_password, f"{legacy_salt}${legacy_hash}"))

    def test_database_backed_sessions_and_expiration(self):
        """Sessions remain readable across handlers and expired tokens are rejected."""
        token = "session-test-token"
        expired_token = "expired-session-test-token"
        user = database.get_user_by_login("ramesh")
        self.assertIsNotNone(user)
        self.addCleanup(database.delete_session, token)
        self.addCleanup(database.delete_session, expired_token)

        database.create_session(token, user["id"], int(time.time()) + 60)
        database.create_session(expired_token, user["id"], int(time.time()) - 1)

        self.assertEqual(database.get_session(token)["user_id"], user["id"])
        self.assertIsNone(database.get_session(expired_token))
        stored = database.query_one("SELECT token_hash FROM sessions WHERE user_id = ?", (user["id"],))
        self.assertNotEqual(stored["token_hash"], token)

    def test_vercel_wsgi_preserves_api_http_status(self):
        """The WSGI adapter must return the status selected by the API handler."""
        from api.index import VercelVillageAppHandler, WSGIHandler, finish_response

        request = WSGIHandler({"PATH_INFO": "/api/login", "REQUEST_METHOD": "POST"})
        handler = object.__new__(VercelVillageAppHandler)
        handler.__dict__.update(request.__dict__)
        handler.send_error_json("Invalid credentials.", status=401)

        response = {}
        body = b"".join(
            finish_response(
                handler,
                lambda status, headers: response.update(status=status, headers=headers),
            )
        )

        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(json.loads(body)["status"], 401)

    def test_legacy_user_schema_migration_preserves_users(self):
        from setup_database import migrate_user_schema

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                mobile TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                village TEXT NOT NULL,
                address TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (41, "Legacy Resident", "9000000001", "legacy.resident@example.com", "Sundarpur",
             "", "old-hash", "villager", "2025-01-01 00:00:00"),
        )
        migrate_user_schema(conn)
        migrate_user_schema(conn)

        user = conn.execute("SELECT id, username, email FROM users WHERE id = 41").fetchone()
        self.assertEqual(user["username"], "legacy.resident")
        self.assertEqual(user["email"], "legacy.resident@example.com")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (id, full_name, username, mobile, email, village, address, password_hash, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (42, "Duplicate Resident", "LEGACY.RESIDENT", "9000000002",
                 "duplicate@example.com", "Sundarpur", "", "hash", "villager", "2025-01-02"),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (id, full_name, username, mobile, email, village, address, password_hash, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (43, "Duplicate Email", "another_resident", "9000000003",
                 "LEGACY.RESIDENT@example.com", "Sundarpur", "", "hash", "villager", "2025-01-03"),
            )
        conn.close()

    def test_user_role_migration_defaults_and_normalizes_without_promotion(self):
        previous_backend = config.DATABASE_BACKEND
        previous_database_path = database.DATABASE_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config.DATABASE_BACKEND = "sqlite"
                database.DATABASE_PATH = Path(temp_dir) / "legacy-users.db"
                conn = database.get_db_connection()
                conn.execute(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL)"
                )
                conn.execute(
                    "INSERT INTO users (id, full_name) VALUES (41, 'Legacy Resident')"
                )
                conn.commit()
                conn.close()

                database.ensure_user_role_schema()
                user = database.query_one(
                    "SELECT id, full_name, role FROM users WHERE id = ?", (41,)
                )
                self.assertEqual(user, {
                    "id": 41,
                    "full_name": "Legacy Resident",
                    "role": "villager",
                })

                database.execute_commit(
                    "UPDATE users SET role = ? WHERE id = ?", (" ADMIN ", 41)
                )
                database.ensure_user_role_schema()
                self.assertEqual(
                    database.query_one("SELECT role FROM users WHERE id = 41")["role"],
                    "admin",
                )
        finally:
            config.DATABASE_BACKEND = previous_backend
            database.DATABASE_PATH = previous_database_path

    def test_mysql_role_migration_when_role_column_already_exists(self):
        previous_backend = config.DATABASE_BACKEND
        try:
            config.DATABASE_BACKEND = "mysql"
            with patch.object(
                database, "query_all", return_value=[{"Field": "role"}]
            ), patch.object(database, "execute_commit") as execute_commit:
                database.ensure_user_role_schema()
            execute_commit.assert_called_once_with(
                "UPDATE users SET role = LOWER(TRIM(role)) "
                "WHERE LOWER(TRIM(role)) IN ('villager', 'admin') AND "
                "BINARY role <> BINARY LOWER(TRIM(role))"
            )
        finally:
            config.DATABASE_BACKEND = previous_backend

    # =================================================================
    # 2. USER AUTHENTICATION & REGISTRATION
    # =================================================================

    def post_api(self, path, body):
        handler = object.__new__(CapturedAPIHandler)
        handler.response = None
        handler.handle_api_post(path, body)
        return handler.response

    def test_user_registration_and_duplicate_prevention(self):
        """Test creating a villager and rejecting repeated login identifiers."""
        test_mobile = "9998887711"
        test_email = "testvillager@village.local"

        # Cleanup if previously exists from prior run
        database.execute_commit(
            "DELETE FROM users WHERE username = ? OR mobile = ? OR email = ?",
            ("kavita_test", test_mobile, test_email),
        )
        self.addCleanup(
            database.execute_commit,
            "DELETE FROM users WHERE username = ? OR mobile = ? OR email = ?",
            ("kavita_test", test_mobile, test_email),
        )

        user_id = database.create_user(
            full_name="Kavita Rane",
            username="kavita_test",
            mobile=test_mobile,
            email=test_email,
            village="Sundarpur",
            address="Plot 5, Ward 1",
            password="SecurePass@123",
            role="villager"
        )
        self.assertGreater(user_id, 0)

        # Verify created record
        user = database.get_user_by_id(user_id)
        self.assertEqual(user["full_name"], "Kavita Rane")
        self.assertEqual(user["role"], "villager")

        # Duplicate mobile must be rejected by unique constraint
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_user(
                full_name="Duplicate User",
                username="another_user",
                mobile=test_mobile,
                email="another@village.local",
                village="Sundarpur",
                address="Somewhere",
                password="TestPass@123",
                role="villager"
            )

        with self.assertRaises(sqlite3.IntegrityError):
            database.create_user(
                full_name="Duplicate User",
                username="kavita_test",
                mobile="9998887712",
                email="another@village.local",
                village="Sundarpur",
                address="Somewhere",
                password="SecurePassword123",
                role="villager",
            )

    def test_registration_login_validation_and_admin_separation(self):
        previous_admin_username = config.ADMIN_USERNAME
        previous_admin_email = config.ADMIN_EMAIL
        previous_admin_password = config.ADMIN_PASSWORD
        self.addCleanup(setattr, config, "ADMIN_USERNAME", previous_admin_username)
        self.addCleanup(setattr, config, "ADMIN_EMAIL", previous_admin_email)
        self.addCleanup(setattr, config, "ADMIN_PASSWORD", previous_admin_password)
        username = "api_new_villager"
        email = "api.new.villager@example.com"
        mobile = "9198765432"
        password = "StrongPassphrase42"
        database.execute_commit(
            "DELETE FROM users WHERE username IN (?, ?)",
            (username, "api_test_admin"),
        )
        self.addCleanup(
            database.execute_commit,
            "DELETE FROM users WHERE username IN (?, ?)",
            (username, "api_test_admin"),
        )
        registration = {
            "full_name": "New Villager",
            "username": username,
            "email": email,
            "mobile": mobile,
            "village": "Sundarpur",
            "address": "Ward 4",
            "password": password,
            "confirm_password": password,
            "role": "admin",
        }

        result = self.post_api("/api/register", registration)
        self.assertEqual(result["status"], 201)
        new_user = database.get_user_by_id(result["data"]["user_id"])
        self.assertEqual(new_user["role"], "villager")
        self.assertEqual(new_user["username"], username)
        stored_user = database.get_user_by_login(email)
        self.assertNotIn(password, stored_user["password_hash"])

        login_responses = []
        for identifier in (email, username, mobile):
            response = self.post_api(
                "/api/login",
                {"identifier": identifier, "password": password, "role": "villager"},
            )
            self.assertEqual(response["status"], 200)
            self.assertEqual(response["data"]["user"]["id"], new_user["id"])
            login_responses.append(response)

        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": email, "password": "IncorrectPassword42", "role": "villager"},
            )["status"],
            401,
        )
        config.ADMIN_USERNAME = username
        config.ADMIN_EMAIL = email
        config.ADMIN_PASSWORD = password + "Extra"
        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": email, "password": password, "role": "admin"},
            )["status"],
            401,
        )

        for changed_field in ("username", "email", "mobile"):
            duplicate = dict(registration)
            duplicate[changed_field] = registration[changed_field].upper() if changed_field != "mobile" else mobile
            self.assertEqual(self.post_api("/api/register", duplicate)["status"], 409)

        invalid_mobile = dict(registration, username="api_bad_mobile", email="bad.mobile@example.com", mobile="12345")
        self.assertEqual(self.post_api("/api/register", invalid_mobile)["status"], 400)
        invalid_email = dict(registration, username="api_bad_email", email="not-an-email",
                             mobile="9198765435")
        self.assertEqual(self.post_api("/api/register", invalid_email)["status"], 400)
        missing_user_id = dict(registration)
        del missing_user_id["username"]
        self.assertEqual(self.post_api("/api/register", missing_user_id)["status"], 400)
        mismatched = dict(registration, username="api_bad_password", email="bad.password@example.com",
                          mobile="9198765433", confirm_password="NotTheSamePassword")
        self.assertEqual(self.post_api("/api/register", mismatched)["status"], 400)

        admin_password = "AdminTestPassphrase42"
        database.create_user(
            full_name="Test Administrator",
            username="api_test_admin",
            mobile="9198765434",
            email="api.test.admin@example.com",
            village="Sundarpur",
            address="",
            password=admin_password,
            role="admin",
        )
        config.ADMIN_USERNAME = ""
        config.ADMIN_EMAIL = ""
        config.ADMIN_PASSWORD = ""
        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": "", "password": admin_password, "role": "admin"},
            )["status"],
            503,
        )
        config.ADMIN_USERNAME = "invalid username!"
        config.ADMIN_EMAIL = "api.test.admin@example.com"
        config.ADMIN_PASSWORD = admin_password
        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": "", "password": admin_password, "role": "admin"},
            )["status"],
            503,
        )
        config.ADMIN_USERNAME = "api_test_admin"
        config.ADMIN_EMAIL = "invalid-email"
        config.ADMIN_PASSWORD = "short"
        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": "", "password": admin_password, "role": "admin"},
            )["status"],
            503,
        )
        config.ADMIN_EMAIL = "api.test.admin@example.com"
        config.ADMIN_PASSWORD = admin_password
        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": "not-the-configured-admin", "password": "IncorrectAdminPassphrase42", "role": "admin"},
            )["status"],
            401,
        )
        admin_login = self.post_api(
            "/api/login",
            {"identifier": "", "password": admin_password, "role": "admin"},
        )
        self.assertEqual(admin_login["status"], 200)
        self.assertEqual(admin_login["data"]["user"]["role"], "admin")
        configured_admin_login = self.post_api(
            "/api/login",
            {
                "identifier": "some-other-username",
                "password": admin_password,
                "role": "admin",
            },
        )
        self.assertEqual(configured_admin_login["status"], 200)
        self.assertEqual(configured_admin_login["data"]["user"]["role"], "admin")

        unauthorized_admin_page = object.__new__(CapturedAPIHandler)
        unauthorized_admin_page.path = "/admin.html"
        unauthorized_admin_page.response_headers = []
        unauthorized_admin_page.send_response = lambda status: setattr(
            unauthorized_admin_page, "status", status
        )
        unauthorized_admin_page.send_header = lambda name, value: (
            unauthorized_admin_page.response_headers.append((name, value))
        )
        unauthorized_admin_page.end_headers = lambda: None
        with patch.object(unauthorized_admin_page, "handle_static_files") as serve_static:
            unauthorized_admin_page.do_GET()
        self.assertEqual(unauthorized_admin_page.status, 302)
        self.assertIn(
            ("Location", "/login.html"), unauthorized_admin_page.response_headers
        )
        serve_static.assert_not_called()

        authorized_admin_page = object.__new__(CapturedAPIHandler)
        authorized_admin_page.path = "/admin.html"
        authorized_admin_page.session_token = admin_login["data"]["token"]
        with patch.object(authorized_admin_page, "handle_static_files") as serve_static:
            authorized_admin_page.do_GET()
        serve_static.assert_called_once_with("/admin.html")

        self.assertEqual(
            self.post_api(
                "/api/login",
                {"identifier": "api_test_admin", "password": admin_password, "role": "villager"},
            )["status"],
            403,
        )

        admin_dashboard = object.__new__(CapturedAPIHandler)
        admin_dashboard.session_token = admin_login["data"]["token"]
        admin_dashboard.handle_api_get("/api/admin/statistics", {})
        self.assertEqual(admin_dashboard.response["status"], 200)

        villager_dashboard = object.__new__(CapturedAPIHandler)
        villager_dashboard.session_token = login_responses[0]["data"]["token"]
        villager_dashboard.handle_api_get("/api/admin/statistics", {})
        self.assertEqual(villager_dashboard.response["status"], 403)

        for login_response in login_responses:
            logout_handler = object.__new__(CapturedAPIHandler)
            logout_handler.session_token = login_response["data"]["token"]
            logout_handler.handle_api_post("/api/logout", {})
            self.assertTrue(logout_handler.response["data"]["success"])
            self.assertIsNone(database.get_session(login_response["data"]["token"]))

        admin_logout = object.__new__(CapturedAPIHandler)
        admin_logout.session_token = admin_login["data"]["token"]
        admin_logout.handle_api_post("/api/logout", {})
        self.assertTrue(admin_logout.response["data"]["success"])
        self.assertIsNone(database.get_session(admin_login["data"]["token"]))
        admin_dashboard_after_logout = object.__new__(CapturedAPIHandler)
        admin_dashboard_after_logout.session_token = admin_login["data"]["token"]
        admin_dashboard_after_logout.handle_api_get("/api/admin/statistics", {})
        self.assertEqual(admin_dashboard_after_logout.response["status"], 403)
        self.assertIsNotNone(database.get_user_by_login(username))
        database.execute_commit("DELETE FROM users WHERE username IN (?, ?)", (username, "api_test_admin"))

    def test_configured_admin_credentials_rotate_existing_account(self):
        from setup_database import seed_configured_admin

        settings = (
            "ADMIN_BOOTSTRAP_USERNAME",
            "ADMIN_BOOTSTRAP_NAME",
            "ADMIN_BOOTSTRAP_EMAIL",
            "ADMIN_BOOTSTRAP_MOBILE",
            "ADMIN_BOOTSTRAP_PASSWORD",
        )
        previous_settings = {name: getattr(config, name) for name in settings}

        def restore_settings():
            for name, value in previous_settings.items():
                setattr(config, name, value)

        self.addCleanup(restore_settings)
        self.addCleanup(
            database.execute_commit,
            "DELETE FROM users WHERE username = ?",
            ("rotation_admin",),
        )
        database.execute_commit("DELETE FROM users WHERE username = ?", ("rotation_admin",))
        database.create_user(
            full_name="Old Administrator",
            username="rotation_admin",
            mobile="9000000096",
            email="rotation.admin@example.com",
            village="Sundarpur",
            address="",
            password="OldAdminPassword42",
            role="admin",
        )

        config.ADMIN_BOOTSTRAP_USERNAME = "rotation_admin"
        config.ADMIN_BOOTSTRAP_NAME = "Rotated Administrator"
        config.ADMIN_BOOTSTRAP_EMAIL = "rotation.admin@example.com"
        config.ADMIN_BOOTSTRAP_MOBILE = "9000000096"
        config.ADMIN_BOOTSTRAP_PASSWORD = "NewAdminPassword42"
        seed_configured_admin()

        admin = database.get_user_by_login("rotation_admin")
        self.assertEqual(admin["full_name"], "Rotated Administrator")
        self.assertTrue(database.verify_password("NewAdminPassword42", admin["password_hash"]))
        self.assertFalse(database.verify_password("OldAdminPassword42", admin["password_hash"]))

    def test_production_admin_setup_changes_only_existing_admin_account(self):
        import setup_admin

        previous_settings = (
            config.DATABASE_BACKEND,
            config.ADMIN_USERNAME,
            config.ADMIN_EMAIL,
            config.ADMIN_PASSWORD,
        )
        self.addCleanup(
            setattr, config, "DATABASE_BACKEND", previous_settings[0]
        )
        self.addCleanup(setattr, config, "ADMIN_USERNAME", previous_settings[1])
        self.addCleanup(setattr, config, "ADMIN_EMAIL", previous_settings[2])
        self.addCleanup(setattr, config, "ADMIN_PASSWORD", previous_settings[3])

        config.DATABASE_BACKEND = "mysql"
        config.ADMIN_USERNAME = "existing_admin"
        config.ADMIN_EMAIL = "new.admin@example.com"
        config.ADMIN_PASSWORD = "NewStrongAdminPassword42!"
        account = {
            "id": 27,
            "role": "admin",
            "email": "old.admin@example.com",
        }
        with patch.object(database, "get_user_by_login", return_value=account), patch.object(
            database, "query_one", return_value=None
        ), patch.object(database, "hash_password", return_value="new-hash") as hash_password, patch.object(
            database, "execute_commit", return_value=1
        ) as execute_commit:
            setup_admin.configure_existing_admin()

        hash_password.assert_called_once_with(config.ADMIN_PASSWORD)
        execute_commit.assert_called_once_with(
            "UPDATE users SET email = ?, password_hash = ? "
            "WHERE id = ? AND role = 'admin'",
            ("new.admin@example.com", "new-hash", 27),
        )

        with patch.object(database, "get_user_by_login", return_value={
            "id": 28, "role": "villager", "email": "citizen@example.com"
        }), patch.object(database, "execute_commit") as blocked_update:
            with self.assertRaisesRegex(ValueError, "existing administrator"):
                setup_admin.configure_existing_admin()
        blocked_update.assert_not_called()
    # =================================================================
    # 3. RESOURCES & MULTI-ATTRIBUTE SEARCH
    # =================================================================

    def test_resource_retrieval(self):
        """Ensure resources are loaded from SQLite catalog."""
        resources = database.get_all_resources()
        self.assertGreaterEqual(len(resources), 5)
        names = [r["name"] for r in resources]
        self.assertTrue(any("Primary Health Centre" in n for n in names))

    def test_resource_search_algorithm(self):
        """Test search_resources function with various query keywords."""
        resources = database.get_all_resources()

        # Search for Health
        health_matches = search_resources(resources, "health")
        self.assertGreater(len(health_matches), 0)
        for h in health_matches:
            match_str = f"{h['name']} {h['category']} {h['description']}".lower()
            self.assertIn("health", match_str)

        # Search for "library"
        lib_matches = search_resources(resources, "library")
        self.assertEqual(len(lib_matches), 1)
        self.assertIn("Library", lib_matches[0]["name"])

        # Non-matching query
        no_matches = search_resources(resources, "nonexistentxyz12345")
        self.assertEqual(len(no_matches), 0)

    # =================================================================
    # 4. GRIEVANCE CREATION, CODE GENERATION & TIMELINE
    # =================================================================

    def test_grievance_code_generation_and_workflow(self):
        """Test automatic grievance code generation (GRV-YYYY-XXXX) and timeline updates."""
        admin = database.get_user_by_login("admin@village.local")
        ramesh = database.get_user_by_login("ramesh@village.local")

        grv = database.create_grievance(
            user_id=ramesh["id"],
            category="Sanitation",
            subject="Clogged drain near temple",
            description="Drain overflow on the pedestrian path.",
            location="Ward 1, Lane 2",
            priority="Low"
        )

        self.assertIsNotNone(grv)
        self.assertTrue(grv["grievance_code"].startswith("GRV-"))
        self.assertEqual(grv["status"], "Submitted")

        # Check initial timeline entry
        updates = database.get_grievance_updates(grv["id"])
        self.assertGreaterEqual(len(updates), 1)
        self.assertEqual(updates[0]["status"], "Submitted")

        # Admin advances status to 'Verified' and escalates priority to 'High'
        updated = database.update_grievance_status_and_assignment(
            grievance_id=grv["id"],
            status="Verified",
            priority="High",
            department_id=6,  # Sanitation
            comment="Verified on site. Upgraded priority to High.",
            updated_by=admin["id"] if admin else None
        )
        self.assertTrue(updated)

        refreshed = database.get_grievance_by_id(grv["id"])
        self.assertEqual(refreshed["status"], "Verified")
        self.assertEqual(refreshed["priority"], "High")

        timeline = database.get_grievance_updates(grv["id"])
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[1]["status"], "Verified")

    # =================================================================
    # 5. DATA STRUCTURE: FIFO QUEUE
    # =================================================================

    def test_fifo_grievance_queue(self):
        """Verify GrievanceQueue maintains strict First-In-First-Out behavior."""
        q = GrievanceQueue()
        self.assertTrue(q.is_empty())
        self.assertEqual(q.size(), 0)

        item1 = {"id": 101, "subject": "Issue A"}
        item2 = {"id": 102, "subject": "Issue B"}
        item3 = {"id": 103, "subject": "Issue C"}

        q.enqueue(item1)
        q.enqueue(item2)
        q.enqueue(item3)

        self.assertEqual(q.size(), 3)
        self.assertEqual(q.peek()["id"], 101)

        # Dequeue must return items in exact order of arrival
        first_out = q.dequeue()
        self.assertEqual(first_out["id"], 101)

        second_out = q.dequeue()
        self.assertEqual(second_out["id"], 102)

        third_out = q.dequeue()
        self.assertEqual(third_out["id"], 103)

        self.assertTrue(q.is_empty())
        self.assertIsNone(q.dequeue())

    # =================================================================
    # 6. DATA STRUCTURE: HEAP-BASED PRIORITY QUEUE
    # =================================================================

    def test_priority_queue_ordering(self):
        """
        Verify GrievancePriorityQueue extracts items in strict priority order:
        Emergency > High > Medium > Low
        """
        pq = GrievancePriorityQueue()
        self.assertTrue(pq.is_empty())

        low_item = {"id": 1, "subject": "Street paint faded", "priority": "Low"}
        medium_item = {"id": 2, "subject": "Park bench broken", "priority": "Medium"}
        high_item = {"id": 3, "subject": "Transformer spark", "priority": "High"}
        emergency_item = {"id": 4, "subject": "Drinking water poisoned/pipeline ruptured", "priority": "Emergency"}

        # Push in random/reverse priority order
        pq.push(low_item)
        pq.push(medium_item)
        pq.push(emergency_item)
        pq.push(high_item)

        self.assertEqual(pq.size(), 4)

        # 1st out: Emergency
        p1 = pq.pop()
        self.assertEqual(p1["priority"], "Emergency")
        self.assertEqual(p1["id"], 4)

        # 2nd out: High
        p2 = pq.pop()
        self.assertEqual(p2["priority"], "High")
        self.assertEqual(p2["id"], 3)

        # 3rd out: Medium
        p3 = pq.pop()
        self.assertEqual(p3["priority"], "Medium")
        self.assertEqual(p3["id"], 2)

        # 4th out: Low
        p4 = pq.pop()
        self.assertEqual(p4["priority"], "Low")
        self.assertEqual(p4["id"], 1)

        self.assertTrue(pq.is_empty())

    def test_priority_queue_to_sorted_list(self):
        """Verify to_sorted_list drains a copy without modifying the queue."""
        pq = GrievancePriorityQueue()
        pq.push({"id": 10, "priority": "Low"})
        pq.push({"id": 20, "priority": "Emergency"})
        pq.push({"id": 30, "priority": "High"})

        sorted_list = pq.to_sorted_list()
        self.assertEqual(len(sorted_list), 3)
        self.assertEqual([x["priority"] for x in sorted_list], ["Emergency", "High", "Low"])
        # Original queue size should remain unchanged
        self.assertEqual(pq.size(), 3)

    # =================================================================
    # 7. DATA STRUCTURES: SEARCHING AND SORTING
    # =================================================================

    def test_grievance_search(self):
        """Test searching grievances by code and keyword."""
        all_grv = database.get_all_grievances()
        matches = search_grievances(all_grv, "pipeline")
        self.assertGreater(len(matches), 0)
        self.assertTrue(any("pipeline" in m["subject"].lower() or "pipeline" in m["description"].lower() for m in matches))

    def test_grievance_sorting(self):
        """Test sorting grievances by priority, date, and status."""
        all_grv = database.get_all_grievances()

        by_priority = sort_grievances_by_priority(all_grv)
        weights = [config.PRIORITY_WEIGHTS.get(g["priority"], 3) for g in by_priority]
        # Verify non-decreasing weights (1 <= 2 <= 3 <= 4)
        for i in range(len(weights) - 1):
            self.assertLessEqual(weights[i], weights[i+1])

        by_date = sort_grievances_by_date(all_grv, reverse=True)
        for i in range(len(by_date) - 1):
            self.assertGreaterEqual(by_date[i]["created_at"], by_date[i+1]["created_at"])


if __name__ == "__main__":
    unittest.main()
