"""
Database Access Layer for Village Resources and Grievance Management System.
Handles SQLite connections, parameterized queries, password hashing, and CRUD operations.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from config import DATABASE_PATH, SCHEMA_PATH, SEED_PATH, PRIORITY_WEIGHTS


def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    Enables foreign keys and sets row_factory to sqlite3.Row for dict-like access.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================================
# PASSWORD HASHING (PBKDF2-HMAC-SHA256 - Python Standard Library)
# =====================================================================

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt.
    Returns string format: salt_hex$hash_hex
    """
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    ).hex()
    return f"{salt}${pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plain password against stored salt_hex$hash_hex.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    try:
        salt, expected_hash = stored_hash.split("$", 1)
        calc_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        ).hex()
        return secrets.compare_digest(calc_hash, expected_hash)
    except Exception:
        return False


# =====================================================================
# DATABASE HELPER UTILITIES
# =====================================================================

def query_all(query: str, params: tuple = ()) -> list:
    """Executes a SELECT query and returns a list of dictionaries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def query_one(query: str, params: tuple = ()) -> dict:
    """Executes a SELECT query and returns a single dictionary or None."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute_commit(query: str, params: tuple = ()) -> int:
    """Executes an INSERT/UPDATE/DELETE query and commits. Returns rowcount."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount


def execute_insert(query: str, params: tuple = ()) -> int:
    """Executes an INSERT query and commits. Returns the lastrowid."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


# =====================================================================
# USERS
# =====================================================================

def create_user(full_name: str, mobile: str, email: str, village: str,
                address: str, password: str, role: str = "villager") -> int:
    """Creates a new user record with securely hashed password."""
    pw_hash = hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO users (full_name, mobile, email, village, address, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    return execute_insert(sql, (full_name.strip(), mobile.strip(), (email or "").strip().lower() or None,
                                village.strip(), address.strip(), pw_hash, role, created_at))


def get_user_by_id(user_id: int) -> dict:
    """Fetches user record without password hash."""
    sql = "SELECT id, full_name, mobile, email, village, address, role, created_at FROM users WHERE id = ?"
    return query_one(sql, (user_id,))


def get_user_by_login(identifier: str) -> dict:
    """
    Finds a user by email or mobile phone. Includes password_hash for auth validation.
    """
    identifier_clean = identifier.strip().lower()
    sql = "SELECT * FROM users WHERE LOWER(email) = ? OR mobile = ?"
    return query_one(sql, (identifier_clean, identifier.strip()))


def get_all_users() -> list:
    """Returns all users without password hashes."""
    sql = "SELECT id, full_name, mobile, email, village, address, role, created_at FROM users ORDER BY id ASC"
    return query_all(sql)


# =====================================================================
# DEPARTMENTS
# =====================================================================

def get_all_departments() -> list:
    """Fetches list of all departments."""
    sql = "SELECT * FROM departments ORDER BY name ASC"
    return query_all(sql)


def get_department_by_id(dept_id: int) -> dict:
    sql = "SELECT * FROM departments WHERE id = ?"
    return query_one(sql, (dept_id,))


def create_department(name: str, contact: str, description: str) -> int:
    sql = "INSERT INTO departments (name, contact, description) VALUES (?, ?, ?)"
    return execute_insert(sql, (name.strip(), contact.strip(), description.strip()))


def update_department(dept_id: int, name: str, contact: str, description: str) -> int:
    sql = "UPDATE departments SET name = ?, contact = ?, description = ? WHERE id = ?"
    return execute_commit(sql, (name.strip(), contact.strip(), description.strip(), dept_id))


def delete_department(dept_id: int) -> int:
    sql = "DELETE FROM departments WHERE id = ?"
    return execute_commit(sql, (dept_id,))


# =====================================================================
# RESOURCES
# =====================================================================

def get_all_resources() -> list:
    """Returns all resources ordered by category and name."""
    sql = "SELECT * FROM resources ORDER BY category ASC, name ASC"
    return query_all(sql)


def get_resource_by_id(resource_id: int) -> dict:
    sql = "SELECT * FROM resources WHERE id = ?"
    return query_one(sql, (resource_id,))


def create_resource(name: str, category: str, location: str, contact: str,
                    availability: str, description: str) -> int:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO resources (name, category, location, contact, availability, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return execute_insert(sql, (name.strip(), category.strip(), location.strip(),
                                contact.strip(), availability.strip(), description.strip(), created_at))


def update_resource(resource_id: int, name: str, category: str, location: str,
                    contact: str, availability: str, description: str) -> int:
    sql = """
        UPDATE resources
        SET name = ?, category = ?, location = ?, contact = ?, availability = ?, description = ?
        WHERE id = ?
    """
    return execute_commit(sql, (name.strip(), category.strip(), location.strip(),
                                contact.strip(), availability.strip(), description.strip(), resource_id))


def delete_resource(resource_id: int) -> int:
    sql = "DELETE FROM resources WHERE id = ?"
    return execute_commit(sql, (resource_id,))


# =====================================================================
# GRIEVANCES & WORKFLOW
# =====================================================================

def generate_grievance_code() -> str:
    """
    Generates a unique sequential grievance code like GRV-2026-0001.
    """
    year = datetime.now().year
    prefix = f"GRV-{year}-"
    sql = "SELECT grievance_code FROM grievances WHERE grievance_code LIKE ? ORDER BY id DESC LIMIT 1"
    last = query_one(sql, (f"{prefix}%",))
    if last and last["grievance_code"]:
        try:
            seq = int(last["grievance_code"].split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_grievance(user_id: int, category: str, subject: str, description: str,
                     location: str, priority: str = "Medium") -> dict:
    """
    Inserts a new grievance into the database and generates an initial 'Submitted' update event.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = generate_grievance_code()
    if priority not in PRIORITY_WEIGHTS:
        priority = "Medium"

    sql = """
        INSERT INTO grievances (grievance_code, user_id, category, subject, description,
                                location, priority, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?)
    """
    grv_id = execute_insert(sql, (code, user_id, category.strip(), subject.strip(),
                                   description.strip(), location.strip(), priority, now, now))

    # Add initial update entry in timeline
    add_grievance_update(
        grievance_id=grv_id,
        status="Submitted",
        comment="Grievance successfully submitted by resident.",
        updated_by=user_id
    )

    return get_grievance_by_id(grv_id)


def get_grievance_by_id(grievance_id: int) -> dict:
    """Fetches grievance along with department name and submitter info."""
    sql = """
        SELECT g.*, u.full_name as submitter_name, u.mobile as submitter_mobile,
               u.village as submitter_village, d.name as department_name
        FROM grievances g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN departments d ON g.department_id = d.id
        WHERE g.id = ?
    """
    return query_one(sql, (grievance_id,))


def get_grievance_by_code(code: str) -> dict:
    """Fetches grievance by unique grievance_code."""
    sql = """
        SELECT g.*, u.full_name as submitter_name, u.mobile as submitter_mobile,
               u.village as submitter_village, d.name as department_name
        FROM grievances g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN departments d ON g.department_id = d.id
        WHERE UPPER(g.grievance_code) = UPPER(?)
    """
    return query_one(sql, (code.strip(),))


def get_grievances_by_user(user_id: int) -> list:
    """Returns all grievances filed by a specific villager."""
    sql = """
        SELECT g.*, d.name as department_name
        FROM grievances g
        LEFT JOIN departments d ON g.department_id = d.id
        WHERE g.user_id = ?
        ORDER BY g.id DESC
    """
    return query_all(sql, (user_id,))


def get_all_grievances() -> list:
    """Returns all grievances for admin views."""
    sql = """
        SELECT g.*, u.full_name as submitter_name, u.mobile as submitter_mobile,
               u.village as submitter_village, d.name as department_name
        FROM grievances g
        JOIN users u ON g.user_id = u.id
        LEFT JOIN departments d ON g.department_id = d.id
        ORDER BY g.id DESC
    """
    return query_all(sql)


def update_grievance_status_and_assignment(grievance_id: int, status: str = None,
                                           priority: str = None, department_id: int = None,
                                           comment: str = None, updated_by: int = None) -> bool:
    """
    Updates grievance status, priority, and/or department. Records a timeline update entry.
    """
    current = get_grievance_by_id(grievance_id)
    if not current:
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_status = status if status else current["status"]
    new_priority = priority if priority else current["priority"]
    new_dept = department_id if department_id is not None else current["department_id"]

    sql = """
        UPDATE grievances
        SET status = ?, priority = ?, department_id = ?, updated_at = ?
        WHERE id = ?
    """
    execute_commit(sql, (new_status, new_priority, new_dept, now, grievance_id))

    # Add audit update record
    msg_parts = []
    if status and status != current["status"]:
        msg_parts.append(f"Status changed to {status}")
    if priority and priority != current["priority"]:
        msg_parts.append(f"Priority changed to {priority}")
    if department_id is not None and department_id != current["department_id"]:
        dept_record = get_department_by_id(department_id) if department_id else None
        dept_name = dept_record["name"] if dept_record else "Unassigned"
        msg_parts.append(f"Department assigned to {dept_name}")

    action_summary = "; ".join(msg_parts) if msg_parts else f"Status: {new_status}"
    full_comment = f"{action_summary}. {comment.strip()}" if comment and comment.strip() else action_summary

    add_grievance_update(
        grievance_id=grievance_id,
        status=new_status,
        comment=full_comment,
        updated_by=updated_by
    )
    return True


def add_grievance_update(grievance_id: int, status: str, comment: str, updated_by: int = None) -> int:
    """Adds a status update record to the grievance timeline."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO grievance_updates (grievance_id, status, comment, updated_by, created_at)
        VALUES (?, ?, ?, ?, ?)
    """
    return execute_insert(sql, (grievance_id, status, comment, updated_by, now))


def get_grievance_updates(grievance_id: int) -> list:
    """Returns chronological timeline updates for a grievance."""
    sql = """
        SELECT gu.*, u.full_name as updated_by_name, u.role as updated_by_role
        FROM grievance_updates gu
        LEFT JOIN users u ON gu.updated_by = u.id
        WHERE gu.grievance_id = ?
        ORDER BY gu.id ASC
    """
    return query_all(sql, (grievance_id,))


# =====================================================================
# ANNOUNCEMENTS
# =====================================================================

def get_all_announcements() -> list:
    """Returns all announcements sorted by announcement date descending."""
    sql = "SELECT * FROM announcements ORDER BY announcement_date DESC, id DESC"
    return query_all(sql)


def get_announcement_by_id(announcement_id: int) -> dict:
    sql = "SELECT * FROM announcements WHERE id = ?"
    return query_one(sql, (announcement_id,))


def create_announcement(title: str, description: str, announcement_date: str) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO announcements (title, description, announcement_date, created_at)
        VALUES (?, ?, ?, ?)
    """
    return execute_insert(sql, (title.strip(), description.strip(), announcement_date.strip(), now))


def update_announcement(announcement_id: int, title: str, description: str, announcement_date: str) -> int:
    sql = """
        UPDATE announcements
        SET title = ?, description = ?, announcement_date = ?
        WHERE id = ?
    """
    return execute_commit(sql, (title.strip(), description.strip(), announcement_date.strip(), announcement_id))


def delete_announcement(announcement_id: int) -> int:
    sql = "DELETE FROM announcements WHERE id = ?"
    return execute_commit(sql, (announcement_id,))


# =====================================================================
# STATISTICS & REPORTS
# =====================================================================

def get_admin_statistics() -> dict:
    """Computes high-level counts for dashboard summary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        total_users = cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'villager'").fetchone()[0]
        total_grievances = cursor.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
        pending = cursor.execute("SELECT COUNT(*) FROM grievances WHERE status IN ('Submitted', 'Verified', 'Assigned')").fetchone()[0]
        in_progress = cursor.execute("SELECT COUNT(*) FROM grievances WHERE status = 'In Progress'").fetchone()[0]
        resolved = cursor.execute("SELECT COUNT(*) FROM grievances WHERE status = 'Resolved'").fetchone()[0]
        high_priority = cursor.execute("SELECT COUNT(*) FROM grievances WHERE priority IN ('High', 'Emergency')").fetchone()[0]
        total_resources = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        total_departments = cursor.execute("SELECT COUNT(*) FROM departments").fetchone()[0]

    return {
        "total_users": total_users,
        "total_grievances": total_grievances,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "high_priority": high_priority,
        "total_resources": total_resources,
        "total_departments": total_departments
    }


def get_admin_reports() -> dict:
    """Generates detailed aggregations for reports and charts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # By category
        by_category = [
            {"category": row[0], "count": row[1]}
            for row in cursor.execute("SELECT category, COUNT(*) FROM grievances GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
        ]

        # By status
        by_status = [
            {"status": row[0], "count": row[1]}
            for row in cursor.execute("SELECT status, COUNT(*) FROM grievances GROUP BY status ORDER BY COUNT(*) DESC").fetchall()
        ]

        # By priority
        by_priority = [
            {"priority": row[0], "count": row[1]}
            for row in cursor.execute("SELECT priority, COUNT(*) FROM grievances GROUP BY priority").fetchall()
        ]

        # By department
        by_dept = [
            {"department": row[0] or "Unassigned", "count": row[1]}
            for row in cursor.execute("""
                SELECT d.name, COUNT(g.id)
                FROM grievances g
                LEFT JOIN departments d ON g.department_id = d.id
                GROUP BY g.department_id
                ORDER BY COUNT(g.id) DESC
            """).fetchall()
        ]

        stats = get_admin_statistics()

    return {
        "summary": stats,
        "by_category": by_category,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_department": by_dept
    }
