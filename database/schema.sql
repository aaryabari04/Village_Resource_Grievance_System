-- ===================================================
-- Village Resources and Grievance Management System
-- SQLite Database Schema Definition
-- ===================================================

PRAGMA foreign_keys = ON;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    mobile TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    village TEXT NOT NULL,
    address TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'villager' CHECK(role IN ('villager', 'admin')),
    created_at TEXT NOT NULL
);

-- 2. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    contact TEXT,
    description TEXT
);

-- 3. Resources Table
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT,
    contact TEXT,
    availability TEXT,
    description TEXT,
    created_at TEXT NOT NULL
);

-- 4. Grievances Table
CREATE TABLE IF NOT EXISTS grievances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grievance_code TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Emergency')),
    status TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'Verified', 'Assigned', 'In Progress', 'Resolved', 'Rejected')),
    department_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- 5. Announcements Table
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    announcement_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 6. Grievance Updates Table (Tracking timeline)
CREATE TABLE IF NOT EXISTS grievance_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grievance_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    comment TEXT,
    updated_by INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(grievance_id) REFERENCES grievances(id) ON DELETE CASCADE,
    FOREIGN KEY(updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for fast query performance
CREATE INDEX IF NOT EXISTS idx_users_mobile ON users(mobile);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category);
CREATE INDEX IF NOT EXISTS idx_resources_name ON resources(name);
CREATE INDEX IF NOT EXISTS idx_grievances_code ON grievances(grievance_code);
CREATE INDEX IF NOT EXISTS idx_grievances_user ON grievances(user_id);
CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances(status);
CREATE INDEX IF NOT EXISTS idx_grievances_priority ON grievances(priority);
CREATE INDEX IF NOT EXISTS idx_grievances_dept ON grievances(department_id);
CREATE INDEX IF NOT EXISTS idx_updates_grievance ON grievance_updates(grievance_id);
