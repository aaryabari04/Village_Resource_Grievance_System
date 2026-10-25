"""Copy the application's SQLite records into an empty MySQL database."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import config
import database

TABLES = (
    "users",
    "departments",
    "resources",
    "announcements",
    "grievances",
    "grievance_updates",
)

EXPECTED_COLUMNS = {
    "users": (
        "id", "full_name", "username", "mobile", "email", "village",
        "address", "password_hash", "role", "created_at",
    ),
    "departments": ("id", "name", "contact", "description"),
    "resources": (
        "id", "name", "category", "location", "contact", "availability",
        "description", "created_at",
    ),
    "announcements": (
        "id", "title", "description", "announcement_date", "created_at",
    ),
    "grievances": (
        "id", "grievance_code", "user_id", "category", "subject",
        "description", "location", "priority", "status", "department_id",
        "created_at", "updated_at",
    ),
    "grievance_updates": (
        "id", "grievance_id", "status", "comment", "updated_by", "created_at",
    ),
}
TARGET_COLUMNS = {
    **EXPECTED_COLUMNS,
    "sessions": ("token_hash", "user_id", "expires_at"),
}

MYSQL_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        full_name TEXT NOT NULL,
        username VARCHAR(30) NOT NULL,
        mobile VARCHAR(255) NOT NULL,
        email VARCHAR(320) NOT NULL,
        village TEXT NOT NULL,
        address TEXT,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(16) NOT NULL DEFAULT 'villager',
        created_at VARCHAR(32) NOT NULL,
        UNIQUE KEY uq_users_username (username),
        UNIQUE KEY uq_users_mobile (mobile),
        UNIQUE KEY uq_users_email (email),
        CONSTRAINT chk_users_role CHECK (role IN ('villager', 'admin'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(190) NOT NULL,
        contact TEXT,
        description TEXT,
        UNIQUE KEY uq_departments_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS resources (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT,
        contact TEXT,
        availability TEXT,
        description TEXT,
        created_at VARCHAR(32) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS announcements (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        announcement_date VARCHAR(32) NOT NULL,
        created_at VARCHAR(32) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS grievances (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        grievance_code VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NOT NULL,
        category TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT,
        priority VARCHAR(16) NOT NULL DEFAULT 'Medium',
        status VARCHAR(32) NOT NULL DEFAULT 'Submitted',
        department_id BIGINT UNSIGNED,
        created_at VARCHAR(32) NOT NULL,
        updated_at VARCHAR(32) NOT NULL,
        UNIQUE KEY uq_grievances_code (grievance_code),
        KEY idx_grievances_user (user_id),
        KEY idx_grievances_status (status),
        KEY idx_grievances_priority (priority),
        KEY idx_grievances_department (department_id),
        CONSTRAINT chk_grievances_priority CHECK (priority IN ('Low', 'Medium', 'High', 'Emergency')),
        CONSTRAINT chk_grievances_status CHECK (status IN ('Submitted', 'Verified', 'Assigned', 'In Progress', 'Resolved', 'Rejected')),
        CONSTRAINT fk_grievances_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_grievances_department FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS grievance_updates (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        grievance_id BIGINT UNSIGNED NOT NULL,
        status VARCHAR(32) NOT NULL,
        comment TEXT,
        updated_by BIGINT UNSIGNED,
        created_at VARCHAR(32) NOT NULL,
        KEY idx_updates_grievance (grievance_id),
        CONSTRAINT fk_updates_grievance FOREIGN KEY (grievance_id) REFERENCES grievances(id) ON DELETE CASCADE,
        CONSTRAINT fk_updates_user FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        token_hash CHAR(64) NOT NULL PRIMARY KEY,
        user_id BIGINT UNSIGNED NOT NULL,
        expires_at BIGINT NOT NULL,
        INDEX idx_sessions_user (user_id),
        CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


def rows_digest(rows) -> tuple:
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        encoded = json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        count += 1
    return count, digest.hexdigest()


def source_summary(source_path: Path) -> dict:
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source file not found: {source_path}")
    with sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True) as source:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed; migration stopped.")
        existing_tables = {
            row[0]
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            if not row[0].startswith("sqlite_")
        }
        missing = [table for table in TABLES if table not in existing_tables]
        if missing:
            raise ValueError(
                "SQLite source is missing required application tables: " + ", ".join(missing)
            )
        unexpected = existing_tables - set(TABLES) - {"sessions"}
        if unexpected:
            raise ValueError(
                "SQLite source contains tables this migration does not handle: "
                + ", ".join(sorted(unexpected))
            )
        summary = {}
        for table in TABLES:
            columns = tuple(
                row[1] for row in source.execute(f"PRAGMA table_info(`{table}`)")
            )
            if set(columns) != set(EXPECTED_COLUMNS[table]):
                raise ValueError(
                    f"SQLite table {table} has an unexpected schema; migration stopped."
                )
            rows = source.execute(f"SELECT * FROM `{table}` ORDER BY id")
            count, digest = rows_digest(rows)
            summary[table] = (count, digest, columns)
        return summary


def mysql_table_summary(cursor, table: str, columns: tuple) -> tuple:
    selected_columns = ", ".join(f"`{column}`" for column in columns)
    cursor.execute(f"SELECT {selected_columns} FROM `{table}` ORDER BY id")
    return rows_digest(cursor)


def apply_migration(source_path: Path, expected_summary: dict) -> None:
    if config.DATABASE_BACKEND != "mysql":
        raise RuntimeError("Set the GRAMSEVA_DB_* variables before applying a MySQL migration.")

    with sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True) as source:
        connection = database.get_db_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = {row[0] for row in cursor.fetchall()}
            unexpected = existing_tables - set(TARGET_COLUMNS)
            if unexpected:
                raise ValueError(
                    "MySQL target contains unrelated tables; migration stopped: "
                    + ", ".join(sorted(unexpected))
                )
            for statement in MYSQL_SCHEMA:
                cursor.execute(statement)
            connection.commit()

            for table, expected_columns in TARGET_COLUMNS.items():
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                actual_columns = {row[0] for row in cursor.fetchall()}
                if actual_columns != set(expected_columns):
                    raise ValueError(
                        f"MySQL table {table} has an unexpected schema; migration stopped."
                    )
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                if cursor.fetchone()[0] != 0:
                    raise ValueError(
                        f"Target table {table} is not empty; migration stopped without changing its records."
                    )

            connection.commit()
            connection.start_transaction()
            for table in TABLES:
                source_cursor = source.execute(f"SELECT * FROM `{table}` ORDER BY id")
                columns = [description[0] for description in source_cursor.description]
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(f"`{column}`" for column in columns)
                insert_sql = (
                    f"INSERT INTO `{table}` ({column_list}) VALUES ({placeholders})"
                )
                while True:
                    batch = source_cursor.fetchmany(500)
                    if not batch:
                        break
                    cursor.executemany(insert_sql, batch)

            for table in TABLES:
                expected_count, expected_digest, columns = expected_summary[table]
                actual = mysql_table_summary(cursor, table, columns)
                if actual != (expected_count, expected_digest):
                    raise ValueError(
                        f"Post-import verification failed for {table}; transaction rolled back."
                    )
            connection.commit()

            for table in TABLES:
                expected_count, expected_digest, columns = expected_summary[table]
                actual = mysql_table_summary(cursor, table, columns)
                if actual != (expected_count, expected_digest):
                    raise ValueError(
                        f"Committed verification failed for {table}; inspect the target before retrying."
                    )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely copy all six GramSeva application tables from SQLite to MySQL."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=config.DATABASE_PATH,
        help="SQLite source file (default: GRAMSEVA_DATABASE_PATH or village_system.db)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing MySQL tables and import records; target application tables must be empty.",
    )
    args = parser.parse_args()

    try:
        summary = source_summary(args.source)
        print("Verified SQLite source and migration record counts:")
        for table, (count, _, _) in summary.items():
            print(f"  {table}: {count}")
        if not args.apply:
            print("Dry run only; no MySQL connection or data changes were made.")
            print("After configuring and securing the empty MySQL database, rerun with --apply.")
            return 0
        apply_migration(args.source, summary)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Migration stopped: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        code = getattr(exc, "errno", None)
        suffix = f" code={code}" if isinstance(code, int) else ""
        print(
            f"Migration failed: error_type={type(exc).__name__}{suffix}",
            file=sys.stderr,
        )
        return 1

    print("Import and per-table content verification succeeded:")
    for table, (count, _, _) in summary.items():
        print(f"  {table}: {count} records match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
