"""
Database Initialization Script for Village Resources and Grievance Management System.
Creates SQLite tables, indexes, and seeds initial realistic demo data.
Safe to run multiple times.
"""

import sys
import sqlite3
import re
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from config import DATABASE_PATH, SCHEMA_PATH, SEED_PATH
from database import (
    get_db_connection,
    hash_password,
    query_one,
    query_all,
    execute_commit,
    execute_insert,
    create_user,
)


def migrate_user_schema(conn):
    """Add identifiers and uniqueness rules while preserving existing user records."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "username" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT COLLATE NOCASE")

    usernames = set()
    for row in conn.execute("SELECT id, username, email FROM users ORDER BY id").fetchall():
        username = (row["username"] or "").strip().lower()
        if not username:
            email_name = (row["email"] or "").split("@", 1)[0].lower()
            username = re.sub(r"[^a-z0-9_.-]", "", email_name)
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,29}", username):
            username = f"resident{row['id']}"
        if username in usernames:
            suffix = str(row["id"])
            username = f"{username[:30 - len(suffix)]}{suffix}"
        usernames.add(username)
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (username, row["id"]))

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username COLLATE NOCASE)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email COLLATE NOCASE) "
        "WHERE email IS NOT NULL"
    )
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS users_require_username_insert
        BEFORE INSERT ON users
        WHEN NEW.username IS NULL OR TRIM(NEW.username) = ''
        BEGIN
            SELECT RAISE(ABORT, 'username is required');
        END;
        CREATE TRIGGER IF NOT EXISTS users_require_username_update
        BEFORE UPDATE OF username ON users
        WHEN NEW.username IS NULL OR TRIM(NEW.username) = ''
        BEGIN
            SELECT RAISE(ABORT, 'username is required');
        END;
        CREATE TRIGGER IF NOT EXISTS users_require_email_insert
        BEFORE INSERT ON users
        WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
        BEGIN
            SELECT RAISE(ABORT, 'email is required');
        END;
        CREATE TRIGGER IF NOT EXISTS users_require_email_update
        BEFORE UPDATE OF email ON users
        WHEN NEW.email IS NULL OR TRIM(NEW.email) = ''
        BEGIN
            SELECT RAISE(ABORT, 'email is required');
        END;
    """)
    conn.commit()


def seed_configured_admin():
    """Create an administrator only when credentials are explicitly configured."""
    required = (
        config.ADMIN_USERNAME,
        config.ADMIN_NAME,
        config.ADMIN_EMAIL,
        config.ADMIN_MOBILE,
        config.ADMIN_PASSWORD,
    )
    if not any(required):
        return
    if not all(required):
        raise ValueError("All GRAMSEVA_ADMIN_* settings are required to bootstrap an administrator.")
    if (
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,29}", config.ADMIN_USERNAME)
        or not re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
            config.ADMIN_EMAIL,
        )
        or not re.fullmatch(r"[0-9]{10}", config.ADMIN_MOBILE)
        or len(config.ADMIN_PASSWORD) < 8
    ):
        raise ValueError("Configured administrator username, mobile, or password is invalid.")
    existing = query_all(
        "SELECT id, role FROM users WHERE username = ? OR email = ? OR mobile = ?",
        (config.ADMIN_USERNAME.lower(), config.ADMIN_EMAIL, config.ADMIN_MOBILE),
    )
    if any(user["role"] != "admin" for user in existing) or len(existing) > 1:
        raise ValueError("Administrator configuration conflicts with an existing villager account.")
    if existing:
        execute_commit(
            """
            UPDATE users
            SET full_name = ?, username = ?, mobile = ?, email = ?, password_hash = ?
            WHERE id = ?
            """,
            (
                config.ADMIN_NAME,
                config.ADMIN_USERNAME.lower(),
                config.ADMIN_MOBILE,
                config.ADMIN_EMAIL,
                hash_password(config.ADMIN_PASSWORD),
                existing[0]["id"],
            ),
        )
    else:
        create_user(
            full_name=config.ADMIN_NAME,
            username=config.ADMIN_USERNAME,
            mobile=config.ADMIN_MOBILE,
            email=config.ADMIN_EMAIL,
            village="Sundarpur",
            address="Gram Panchayat Office",
            password=config.ADMIN_PASSWORD,
            role="admin",
        )


def init_database():
    """Initializes the database schema and seeds initial departments/resources/announcements."""
    print("=" * 60)
    print("Initializing Village Resources & Grievance Management Database")
    print(f"Database File: {DATABASE_PATH}")
    print("=" * 60)

    # 1. Execute Schema DDL
    print("[1/4] Applying Schema DDL...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        conn.executescript(schema_sql)
        migrate_user_schema(conn)
    print("      [OK] Tables and Indexes created successfully.")

    # 2. Execute Base Seed (Departments, Resources, Announcements)
    print("[2/4] Seeding Departments, Resources, and Announcements...")
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed_sql = f.read()

    with get_db_connection() as conn:
        conn.executescript(seed_sql)
        conn.commit()
    print("      [OK] Base catalog data inserted.")

    # 3. Keep the existing sample residents used by the sample grievance dataset.
    print("[3/4] Seeding sample villager accounts...")
    users_to_seed = [
        {
            "full_name": "Ramesh Patil",
            "username": "ramesh",
            "mobile": "9822011223",
            "email": "ramesh@village.local",
            "village": "Sundarpur",
            "address": "House No. 42, North Para, Sundarpur",
            "password": "Villager@123",
            "role": "villager",
            "created_at": "2026-01-15 10:00:00"
        },
        {
            "full_name": "Sunita Devi",
            "username": "sunita",
            "mobile": "9822011224",
            "email": "sunita@village.local",
            "village": "Sundarpur",
            "address": "Plot 18, Ward 3, Near Old Well, Sundarpur",
            "password": "Villager@123",
            "role": "villager",
            "created_at": "2026-01-20 11:30:00"
        },
        {
            "full_name": "Ajay Sharma",
            "username": "ajay",
            "mobile": "9822011225",
            "email": "ajay@village.local",
            "village": "Sundarpur",
            "address": "Farm House 7, East Canal Road, Sundarpur",
            "password": "Villager@123",
            "role": "villager",
            "created_at": "2026-02-01 14:15:00"
        }
    ]

    for u in users_to_seed:
        existing = query_one(
            "SELECT id FROM users WHERE username = ? OR email = ? OR mobile = ?",
            (u["username"], u["email"], u["mobile"]),
        )
        if not existing:
            pw_hash = hash_password(u["password"])
            execute_insert(
                """
                INSERT INTO users (full_name, username, mobile, email, village, address, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (u["full_name"], u["username"], u["mobile"], u["email"], u["village"], u["address"],
                 pw_hash, u["role"], u["created_at"])
            )
            print(f"      + Created user: {u['email']} ({u['role']})")
        else:
            print(f"      [*] User already exists: {u['email']}")

    seed_configured_admin()

    # 4. Seed Grievances and Updates
    print("[4/4] Seeding Sample Grievances & Status Timelines...")
    admin_user = query_one("SELECT id FROM users WHERE role = 'admin'")
    ramesh_user = query_one("SELECT id FROM users WHERE email = 'ramesh@village.local'")
    sunita_user = query_one("SELECT id FROM users WHERE email = 'sunita@village.local'")
    ajay_user = query_one("SELECT id FROM users WHERE email = 'ajay@village.local'")

    admin_id = admin_user["id"] if admin_user else None
    ramesh_id = ramesh_user["id"] if ramesh_user else 2
    sunita_id = sunita_user["id"] if sunita_user else 3
    ajay_id = ajay_user["id"] if ajay_user else 4

    sample_grievances = [
        {
            "code": "GRV-2026-0001",
            "user_id": ramesh_id,
            "category": "Water Supply",
            "subject": "Main pipeline burst flooding agricultural road",
            "description": "The 6-inch primary drinking water pipeline burst open near North Para culvert. Potable water is flooding the road and several fields, causing water pressure loss in 40 households.",
            "location": "North Para, Near Culvert No. 3",
            "priority": "Emergency",
            "status": "In Progress",
            "department_id": 1,  # Water
            "created_at": "2026-03-20 08:30:00",
            "updated_at": "2026-03-21 10:15:00",
            "timeline": [
                ("Submitted", "Grievance submitted by Ramesh Patil with high urgency.", ramesh_id, "2026-03-20 08:30:00"),
                ("Verified", "Grievance verified on site by Gram Sevak. Escalated to Emergency.", admin_id, "2026-03-20 09:15:00"),
                ("Assigned", "Assigned to Water Department maintenance field crew.", admin_id, "2026-03-20 10:00:00"),
                ("In Progress", "Replacement pipe segment delivered. Welders and excavator active on site.", admin_id, "2026-03-21 10:15:00")
            ]
        },
        {
            "code": "GRV-2026-0002",
            "user_id": sunita_id,
            "category": "Electricity",
            "subject": "Streetlights non-functional creating safety hazard",
            "description": "Four consecutive solar streetlights from Ward 3 intersection to the girls' primary school have been dark for 5 nights. Poses severe safety hazard for residents at dusk.",
            "location": "Ward 3, School Approach Road",
            "priority": "Medium",
            "status": "Assigned",
            "department_id": 2,  # Electricity
            "created_at": "2026-03-21 14:00:00",
            "updated_at": "2026-03-22 11:00:00",
            "timeline": [
                ("Submitted", "Grievance submitted by Sunita Devi.", sunita_id, "2026-03-21 14:00:00"),
                ("Verified", "Verified by Panchayat supervisor.", admin_id, "2026-03-22 09:30:00"),
                ("Assigned", "Work order issued to Junior Engineer, Electricity Department.", admin_id, "2026-03-22 11:00:00")
            ]
        },
        {
            "code": "GRV-2026-0003",
            "user_id": ajay_id,
            "category": "Roads & Infrastructure",
            "subject": "Deep potholes causing vehicle accidents near market",
            "description": "Monsoon damage created severe 1-foot deep potholes along the main market bypass road. Two two-wheelers skidded yesterday. Urgent tar patching required.",
            "location": "Main Market Bypass, Near Krishi Seva Kendra",
            "priority": "High",
            "status": "Verified",
            "department_id": 3,  # PWD
            "created_at": "2026-03-22 11:20:00",
            "updated_at": "2026-03-22 16:45:00",
            "timeline": [
                ("Submitted", "Grievance filed with site photographs.", ajay_id, "2026-03-22 11:20:00"),
                ("Verified", "Inspection conducted by PWD road supervisor. Priority set to High.", admin_id, "2026-03-22 16:45:00")
            ]
        },
        {
            "code": "GRV-2026-0004",
            "user_id": sunita_id,
            "category": "Sanitation",
            "subject": "Open drainage overflow and irregular waste collection",
            "description": "The open drainage channel in Ward 2 is choked with silt and plastic debris, overflowing onto footpaths. Mosquito breeding has increased substantially.",
            "location": "Ward 2, Lane 4, Behind Temple",
            "priority": "Medium",
            "status": "Submitted",
            "department_id": 6,  # Sanitation
            "created_at": "2026-03-23 07:15:00",
            "updated_at": "2026-03-23 07:15:00",
            "timeline": [
                ("Submitted", "Grievance submitted by resident.", sunita_id, "2026-03-23 07:15:00")
            ]
        },
        {
            "code": "GRV-2026-0005",
            "user_id": ramesh_id,
            "category": "Health",
            "subject": "Shortage of essential diabetes and BP tablets at PHC",
            "description": "Primary Health Centre medicine counter ran out of regular hypertension and diabetes tablets for the past 10 days. Elderly villagers traveling 25 km to tehsil town.",
            "location": "Primary Health Centre Dispensary",
            "priority": "High",
            "status": "Resolved",
            "department_id": 4,  # Health
            "created_at": "2026-03-12 10:00:00",
            "updated_at": "2026-03-18 15:30:00",
            "timeline": [
                ("Submitted", "Resident submitted medicine availability grievance.", ramesh_id, "2026-03-12 10:00:00"),
                ("Verified", "Verified with Medical Officer in charge of PHC.", admin_id, "2026-03-12 14:00:00"),
                ("Assigned", "Transferred to District Health Logistics & Warehousing.", admin_id, "2026-03-13 09:00:00"),
                ("In Progress", "Emergency batch order dispatched from district warehouse.", admin_id, "2026-03-15 11:30:00"),
                ("Resolved", "New stock of 5,000 tablets received and verified at PHC dispensary. Free distribution resumed.", admin_id, "2026-03-18 15:30:00")
            ]
        }
    ]

    for g in sample_grievances:
        existing = query_one("SELECT id FROM grievances WHERE grievance_code = ?", (g["code"],))
        if not existing:
            sql_grv = """
                INSERT INTO grievances (grievance_code, user_id, category, subject, description,
                                        location, priority, status, department_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            grv_id = execute_insert(sql_grv, (
                g["code"], g["user_id"], g["category"], g["subject"], g["description"],
                g["location"], g["priority"], g["status"], g["department_id"], g["created_at"], g["updated_at"]
            ))

            for status_val, comment_val, up_by, created_t in g["timeline"]:
                execute_insert(
                    """
                    INSERT INTO grievance_updates (grievance_id, status, comment, updated_by, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (grv_id, status_val, comment_val, up_by, created_t)
                )
            print(f"      + Seeded Grievance: {g['code']} ({g['priority']} - {g['status']})")
        else:
            print(f"      [*] Grievance already exists: {g['code']}")

    print("=" * 60)
    print("Database Setup Completed Successfully!")
    print("Administrator accounts are created only from explicit environment configuration.")
    print("Public villager accounts can be created from the registration page.")
    print("=" * 60)


if __name__ == "__main__":
    init_database()
