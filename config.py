"""
Configuration module for Village Resources and Grievance Management System.
Contains application settings, database paths, and system constants.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Server settings
HOST = "127.0.0.1"
PORT = 8000

# Database settings
DATABASE_PATH = BASE_DIR / "village_system.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"

# Static / Frontend directories
FRONTEND_DIR = BASE_DIR / "frontend"
CSS_DIR = BASE_DIR / "css"
JS_DIR = BASE_DIR / "js"
ASSETS_DIR = BASE_DIR / "assets"

# Session settings
SESSION_COOKIE_NAME = "village_session_id"
SESSION_LIFETIME_SECONDS = 86400  # 24 hours

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
