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
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
import database
from data_structures import (
    GrievanceQueue,
    GrievancePriorityQueue,
    search_resources,
    search_grievances,
    sort_grievances_by_priority,
    sort_grievances_by_date,
    sort_grievances_by_status
)


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
        conn.close()

        expected_tables = ["users", "departments", "resources", "grievances", "announcements", "grievance_updates"]
        for table in expected_tables:
            self.assertIn(table, tables, f"Expected table '{table}' not found in database.")

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

    # =================================================================
    # 2. USER AUTHENTICATION & REGISTRATION
    # =================================================================

    def test_admin_demo_account_exists(self):
        """Verify demo admin account is properly seeded and password verifies."""
        admin = database.get_user_by_login("admin@village.local")
        self.assertIsNotNone(admin, "Demo admin account admin@village.local should exist.")
        self.assertEqual(admin["role"], "admin")
        self.assertTrue(database.verify_password("Admin@123", admin["password_hash"]))

    def test_user_registration_and_duplicate_prevention(self):
        """Test creating a new villager and preventing duplicate phone numbers."""
        test_mobile = "9998887711"
        test_email = "testvillager@village.local"

        # Cleanup if previously exists from prior run
        database.execute_commit("DELETE FROM users WHERE mobile = ? OR email = ?", (test_mobile, test_email))

        user_id = database.create_user(
            full_name="Kavita Rane",
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
                mobile=test_mobile,
                email="another@village.local",
                village="Sundarpur",
                address="Somewhere",
                password="TestPass@123",
                role="villager"
            )

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
            updated_by=admin["id"]
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
