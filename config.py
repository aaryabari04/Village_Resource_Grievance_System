"""
Configuration module for Village Resources and Grievance Management System.
Contains application settings, database paths, and system constants.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env", override=False)

# Server settings
HOST = "127.0.0.1"
PORT = 8000

# Database settings
DATABASE_PATH = Path(os.getenv("GRAMSEVA_DATABASE_PATH", str(BASE_DIR / "village_system.db")))
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"
MYSQL_ENV_NAMES = {
    "host": "GRAMSEVA_DB_HOST",
    "port": "GRAMSEVA_DB_PORT",
    "database": "GRAMSEVA_DB_NAME",
    "user": "GRAMSEVA_DB_USER",
    "password": "GRAMSEVA_DB_PASSWORD",
    "ssl_ca": "GRAMSEVA_DB_SSL_CA",
}
MYSQL_SETTINGS = {
    key: (
        os.getenv(env_name, "")
        if key in ("password", "ssl_ca")
        else os.getenv(env_name, "").strip()
    )
    for key, env_name in MYSQL_ENV_NAMES.items()
}
MYSQL_SETTINGS["port"] = MYSQL_SETTINGS["port"] or "3306"
DATABASE_BACKEND = (
    "mysql"
    if any(
        MYSQL_SETTINGS[key]
        for key in ("host", "database", "user", "password", "ssl_ca")
    )
    else "sqlite"
)
IS_VERCEL = os.getenv("VERCEL", "").lower() == "1"


def mysql_connection_settings() -> dict:
    """Validate and return the server-only MySQL connection settings."""
    required = ("host", "database", "user", "password", "ssl_ca")
    missing = [
        MYSQL_ENV_NAMES[key]
        for key in required
        if not MYSQL_SETTINGS[key]
    ]
    if missing:
        raise RuntimeError(
            "MySQL configuration is incomplete; set " + ", ".join(missing)
        )
    try:
        port = int(MYSQL_SETTINGS["port"])
    except ValueError as exc:
        raise RuntimeError("GRAMSEVA_DB_PORT must be a valid TCP port.") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("GRAMSEVA_DB_PORT must be a valid TCP port.")

    return {
        "host": MYSQL_SETTINGS["host"],
        "port": port,
        "database": MYSQL_SETTINGS["database"],
        "user": MYSQL_SETTINGS["user"],
        "password": MYSQL_SETTINGS["password"],
        "ssl_ca": MYSQL_SETTINGS["ssl_ca"],
    }

# Static / Frontend directories
FRONTEND_DIR = BASE_DIR / "frontend"
CSS_DIR = BASE_DIR / "css"
JS_DIR = BASE_DIR / "js"
ASSETS_DIR = BASE_DIR / "assets"

# Session settings
SESSION_COOKIE_NAME = "village_session_id"
SESSION_LIFETIME_SECONDS = 86400  # 24 hours

# Administrator login credentials. ADMIN_PASSWORD is required for production.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Optional one-time SQLite administrator bootstrap settings.
ADMIN_BOOTSTRAP_USERNAME = os.getenv("GRAMSEVA_ADMIN_USERNAME", "").strip()
ADMIN_BOOTSTRAP_NAME = os.getenv("GRAMSEVA_ADMIN_NAME", "").strip()
ADMIN_BOOTSTRAP_EMAIL = os.getenv("GRAMSEVA_ADMIN_EMAIL", "").strip().lower()
ADMIN_BOOTSTRAP_MOBILE = os.getenv("GRAMSEVA_ADMIN_MOBILE", "").strip()
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("GRAMSEVA_ADMIN_PASSWORD", "")

# Priority levels and corresponding weights for Priority Queue
# Lower numerical value indicates higher priority (Emergency is highest rank: 1)
PRIORITY_WEIGHTS = {
    "Emergency": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4
}

ALLOWED_PRIORITIES = list(PRIORITY_WEIGHTS.keys())

# Grievance workflow statuses
ALLOWED_STATUSES = [
    "Submitted",
    "Verified",
    "Assigned",
    "In Progress",
    "Resolved",
    "Rejected"
]

# User roles
ROLES = ["villager", "admin"]
