"""
Database Access Layer for Village Resources and Grievance Management System.
Handles SQLite connections, parameterized queries, password hashing, and CRUD operations.
"""

import sqlite3
import hashlib
import secrets
import hmac
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import config
from config import DATABASE_PATH, PRIORITY_WEIGHTS

PASSWORD_HASH_ITERATIONS = 600_000
LEGACY_PASSWORD_HASH_ITERATIONS = 100_000
_MYSQL_POOL = None
_MYSQL_POOL_LOCK = threading.Lock()
_MYSQL_CA_FILE = None


def _mysql_pool():
    """Create one small connection pool per warm serverless instance."""
    global _MYSQL_POOL, _MYSQL_CA_FILE
    if _MYSQL_POOL is None:
        with _MYSQL_POOL_LOCK:
            if _MYSQL_POOL is None:
                from mysql.connector.pooling import MySQLConnectionPool

                settings = config.mysql_connection_settings()
                ca_value = settings.pop("ssl_ca")
                if "-----BEGIN CERTIFICATE-----" in ca_value:
                    ca_digest = hashlib.sha256(ca_value.encode("utf-8")).hexdigest()[:16]
                    _MYSQL_CA_FILE = Path(tempfile.gettempdir()) / f"gramseva-mysql-ca-{ca_digest}.pem"
                    if not _MYSQL_CA_FILE.exists():
                        try:
                            _MYSQL_CA_FILE.write_text(ca_value, encoding="utf-8")
                            _MYSQL_CA_FILE.chmod(0o600)
                        except FileExistsError:
                            pass
                    ca_path = str(_MYSQL_CA_FILE)
                else:
                    ca_path = str(Path(ca_value).expanduser())
                    if not Path(ca_path).is_file():
                        raise RuntimeError("GRAMSEVA_DB_SSL_CA must contain a CA certificate or a readable file path.")

                _MYSQL_POOL = MySQLConnectionPool(
                    pool_name="gramseva",
                    pool_size=5,
                    pool_reset_session=True,
                    connection_timeout=10,
                    ssl_ca=ca_path,
                    ssl_verify_cert=True,
                    ssl_verify_identity=True,
                    **settings,
                )
    return _MYSQL_POOL


def get_db_connection():
    """
    Returns a pooled MySQL connection or a SQLite connection for local development.
    """
    if config.DATABASE_BACKEND == "mysql":
        return _mysql_pool().get_connection()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _managed_connection():
    conn = get_db_connection()
    try:
        yield conn
    except Exception:
        if config.DATABASE_BACKEND == "mysql":
            conn.rollback()
        raise
    finally:
        conn.close()


def _execute(cursor, query: str, params: tuple = ()):
    if config.DATABASE_BACKEND == "mysql":
        query = query.replace("?", "%s")
    return cursor.execute(query, params)


def is_integrity_error(error: Exception) -> bool:
    """Recognize uniqueness and foreign-key violations from either driver."""
    if isinstance(error, sqlite3.IntegrityError):
        return True
    if config.DATABASE_BACKEND == "mysql":
        from mysql.connector import IntegrityError
        return isinstance(error, IntegrityError)
    return False


def check_connection() -> None:
    """Fail explicitly when MySQL or the migrated application schema is unavailable."""
    with _managed_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        if config.DATABASE_BACKEND == "mysql":
            for table in (
                "users",
                "departments",
                "resources",
                "announcements",
                "grievances",
                "grievance_updates",
                "sessions",
            ):
                cursor.execute(f"SELECT 1 FROM `{table}` LIMIT 0")
                cursor.fetchall()


def ensure_session_table() -> None:
    """Apply the additive, non-destructive session-table change."""
    if config.DATABASE_BACKEND == "mysql":
        statement = """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash CHAR(64) NOT NULL PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                expires_at BIGINT NOT NULL,
                INDEX idx_sessions_user (user_id),
                CONSTRAINT fk_sessions_user FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    else:
        statement = """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """
    with _managed_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(statement)
        if config.DATABASE_BACKEND == "mysql":
            conn.commit()
        else:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)"
            )
            conn.commit()


def ensure_user_role_schema() -> None:
    """Add a villager-only default role when missing and canonicalize known roles."""
    if config.DATABASE_BACKEND == "mysql":
        columns = query_all("SHOW COLUMNS FROM users")
        has_role = any(column["Field"] == "role" for column in columns)
        role_difference = "BINARY role <> BINARY LOWER(TRIM(role))"
        if not has_role:
            try:
                execute_commit(
                    "ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'villager'"
                )
            except Exception as exc:
                # Multiple serverless instances may race to apply this additive migration.
                if getattr(exc, "errno", None) != 1060:
                    raise
    else:
        columns = query_all("PRAGMA table_info(users)")
        has_role = any(column["name"] == "role" for column in columns)
        if not has_role:
            execute_commit(
                "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'villager'"
            )
        role_difference = "role <> LOWER(TRIM(role))"

    execute_commit(
        "UPDATE users SET role = LOWER(TRIM(role)) "
        "WHERE LOWER(TRIM(role)) IN ('villager', 'admin') AND "
        + role_difference
    )


def normalize_role(role: str) -> str:
    """Return a canonical stored role, or an empty value for an invalid role."""
    return role.strip().lower() if isinstance(role, str) else ""


# =====================================================================
# PASSWORD HASHING (PBKDF2-HMAC-SHA256 - Python Standard Library)
# =====================================================================

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt.
    Returns a versioned PBKDF2-HMAC-SHA256 hash.
    """
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=PASSWORD_HASH_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a versioned or legacy PBKDF2 hash in constant time.
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt, expected_hash = parts[2], parts[3]
            if iterations != PASSWORD_HASH_ITERATIONS:
                return False
        elif len(parts) == 2:
            iterations = LEGACY_PASSWORD_HASH_ITERATIONS
            salt, expected_hash = parts
        else:
            return False
        calc_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=iterations
        ).hex()
        return hmac.compare_digest(calc_hash, expected_hash)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False


# =====================================================================
# DATABASE HELPER UTILITIES
# =====================================================================

def query_all(query: str, params: tuple = ()) -> list:
    """Executes a SELECT query and returns a list of dictionaries."""
    with _managed_connection() as conn:
        cursor = conn.cursor(dictionary=True) if config.DATABASE_BACKEND == "mysql" else conn.cursor()
        _execute(cursor, query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def query_one(query: str, params: tuple = ()) -> dict:
    """Executes a SELECT query and returns a single dictionary or None."""
    with _managed_connection() as conn:
        cursor = conn.cursor(dictionary=True) if config.DATABASE_BACKEND == "mysql" else conn.cursor()
        _execute(cursor, query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute_commit(query: str, params: tuple = ()) -> int:
    """Executes an INSERT/UPDATE/DELETE query and commits. Returns rowcount."""
    with _managed_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, query, params)
        conn.commit()
        return cursor.rowcount


def execute_insert(query: str, params: tuple = ()) -> int:
    """Executes an INSERT query and commits. Returns the lastrowid."""
    with _managed_connection() as conn:
        cursor = conn.cursor()
        _execute(cursor, query, params)
        conn.commit()
        return cursor.lastrowid


def create_session(token: str, user_id: int, expires_at: int) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    execute_insert(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash, user_id, expires_at),
    )


def get_session(token: str) -> dict:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = query_one(
        "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
        (token_hash,),
    )
    if session and int(session["expires_at"]) <= int(datetime.now().timestamp()):
        delete_session(token)
        return None
    return session


def delete_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    execute_commit("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


# =====================================================================
# USERS
# =====================================================================

def create_user(full_name: str, username: str, mobile: str, email: str, village: str,
                address: str, password: str, role: str = "villager") -> int:
    """Creates a new user record with securely hashed password."""
    role = normalize_role(role)
    if role not in config.ROLES:
        raise ValueError("A valid account role is required.")
    pw_hash = hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """
        INSERT INTO users (full_name, username, mobile, email, village, address, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return execute_insert(sql, (full_name.strip(), username.strip().lower(), mobile.strip(), email.strip().lower(),
                                village.strip(), address.strip(), pw_hash, role, created_at))


def get_user_by_id(user_id: int) -> dict:
    """Fetches user record without password hash."""
    sql = "SELECT id, full_name, username, mobile, email, village, address, role, created_at FROM users WHERE id = ?"
    user = query_one(sql, (user_id,))
    if user:
        user["role"] = normalize_role(user["role"])
    return user


def get_user_by_login(identifier: str) -> dict:
    """
    Finds a user by username, email, or mobile phone. Includes password_hash for auth validation.
    """
    identifier_clean = identifier.strip().lower()
    sql = "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ? OR mobile = ?"
    user = query_one(sql, (identifier_clean, identifier_clean, identifier.strip()))
    if user:
        user["role"] = normalize_role(user["role"])
    return user


def get_all_users() -> list:
    """Returns all users without password hashes."""
    sql = "SELECT id, full_name, username, mobile, email, village, address, role, created_at FROM users ORDER BY id ASC"
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
    with _managed_connection() as conn:
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
    with _managed_connection() as conn:
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
