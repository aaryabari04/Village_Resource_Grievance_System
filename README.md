# Village Resources and Grievance Management System (GramSeva)
**A Full-Stack College Capstone Project**

---

## 📌 1. Project Overview

The **Village Resources and Grievance Management System (GramSeva)** is a digital governance platform designed for rural Gram Panchayats. It enables village residents to easily discover public resources, search services, submit grievances, and track resolution timelines in real time. For administrators, it provides a centralized console to triage complaints using Priority Queues, assign responsible municipal departments, manage public facilities, broadcast announcements, and monitor civic analytics.

### Key Goals:
- Connect villagers with essential village amenities (health clinics, schools, water supply, public libraries, electricity transformers).
- Transparent, algorithmic grievance redressal with automated tracking codes (`GRV-YYYY-XXXX`).
- Multi-language inclusivity with instantaneous support for **English**, **मराठी (Marathi)**, and **हिन्दी (Hindi)**.
- **Python backend** with no framework dependency (no Flask, no Django, no React);
  the production MySQL driver is installed only for database connectivity.

---

## 🏗️ 2. Architectural Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Web Browser                          │
│     Vanilla HTML5 / CSS3 / JavaScript (Trilingual UI)           │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP / REST JSON / Cookies
┌───────────────────────────────▼─────────────────────────────────┐
│              Python Standard Library HTTP Server                │
│    (ThreadingHTTPServer, Custom Router, PBKDF2 Password Hasher) │
├───────────────────────────────┬─────────────────────────────────┤
│    Authentication & Session   │     Data Structures Engine      │
│  Database-backed sessions     │  • FIFO GrievanceQueue          │
│  Role-Based Access Control    │  • Heapq GrievancePriorityQueue │
│                               │  • Multi-attribute Search & Sort│
└───────────────────────────────┴────────────────┬────────────────┘
                                                 │ Parameterized SQL
┌────────────────────────────────────────────────▼────────────────┐
│              SQLite locally / MySQL on Vercel                   │
│   users, resources, departments, grievances, announcements,     │
│   grievance_updates                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 3. Technology Stack

- **Frontend:** HTML5, CSS3 (Modern Responsive Flexbox/Grid, CSS Variables), Vanilla JavaScript (ES6+).
- **Backend:** Python 3.8+:
  - `http.server` & `socketserver` (Multi-threaded HTTP Server)
  - `sqlite3` for local development; `mysql-connector-python` for production MySQL
  - `hashlib` (PBKDF2-HMAC-SHA256 Password Hashing)
  - `heapq` (Min-Heap Priority Queue)
  - `collections.deque` (FIFO Grievance Intake Queue)
  - `json` & `urllib.parse` (API Serialization & Routing)
  - `unittest` (Automated backend verification)
- **Database:** SQLite 3 locally; MySQL 8+ for persistent Vercel deployments.
- **External Dependencies:** MySQL driver is only needed for MySQL deployments.

---

## 📂 4. Project Folder Structure

```
Village_Resource_Grievance_System/
│
├── server.py                   # Multi-threaded HTTP Server & REST API Dispatcher
├── database.py                 # SQLite/MySQL query layer and PBKDF2 auth
├── migrate_to_mysql.py         # Non-destructive SQLite-to-MySQL migration
├── config.py                   # System constants, ports, and priority rankings
├── requirements.txt            # Zero-dependency specification file
├── README.md                   # Complete documentation and setup guide
├── setup_database.py           # Database initialisation and realistic seeding script
├── test_backend.py             # Unittest test suite for backend, DB, queues, and search
├── vercel.json                 # Vercel routing and Python function configuration
├── api/
│   └── index.py                # Vercel WSGI adapter for the existing Python server
│
├── data_structures/            # Core Data Structures Layer
│   ├── __init__.py
│   ├── grievance_queue.py      # FIFO Queue for sequential grievance review
│   ├── priority_queue.py       # Min-Heap Priority Queue (Emergency > High > Medium > Low)
│   └── search_sort.py          # Multi-attribute linear search and multi-key sorting
│
├── database/                   # SQL Schemas & Seed Data
│   ├── schema.sql              # DDL for all 6 tables and indexes
│   └── seed.sql                # Base departments, resources, and announcements
│
├── frontend/                   # HTML5 Web Pages
│   ├── index.html              # Public landing page with hero, services & stats
│   ├── login.html              # Authentication page with Villager/Admin role toggle
│   ├── register.html           # Citizen registration form with client validation
│   ├── dashboard.html          # Villager portal showing personal metrics & complaints
│   ├── resources.html          # Searchable catalog of village facilities & contacts
│   ├── grievance.html          # Grievance submission form with instant code generator
│   ├── track.html              # Public grievance tracking page with vertical timeline
│   ├── announcements.html      # Public notices and Gram Sabha announcements
│   └── admin.html              # Full administrator console with Priority Queue toggle
│
├── css/
│   └── style.css               # Civic service design system, responsive styles, badges
│
├── js/
│   └── script.js               # Translation dictionaries, session manager, UI toasts
│
└── assets/
    └── images/
        └── logo.svg            # Custom vector emblem icon
```

---

## 🧠 5. Data Structures Implementation Details

A major component of this capstone is the explicit implementation and backend utilization of fundamental Computer Science data structures:

| Data Structure | Implementation File | Usage in System | Algorithm / Time Complexity |
| :--- | :--- | :--- | :--- |
| **FIFO Queue** | `data_structures/grievance_queue.py` | Chronological sequential intake of grievances for administrative review. | Uses `collections.deque`. Enqueue: $O(1)$, Dequeue: $O(1)$, Peek: $O(1)$. |
| **Priority Queue** | `data_structures/priority_queue.py` | Triage of urgent complaints: `Emergency (1) > High (2) > Medium (3) > Low (4)`. | Uses Python `heapq` min-heap with sequence counter tie-breaker. Push: $O(\log N)$, Pop: $O(\log N)$, Sorted Drainage: $O(N \log N)$. |
| **Linear Multi-attribute Search** | `data_structures/search_sort.py` | Search across resource name, facility type, location, and description. | Multi-keyword substring matching. Complexity: $O(N \times M)$. |
| **Multi-Criteria Sorting** | `data_structures/search_sort.py` | Sorting grievances by severity weight, submission timestamp, or lifecycle status. | Uses Timsort with custom key functions. Complexity: $O(N \log N)$. |
| **Hash Tables / Dictionaries** | Python native `dict` | In-memory session store, JSON API request/response mapping, priority ranking weights. | Average lookup / insert: $O(1)$. |
| **List** | Python native `list` | Storing and batching database rows before dispatch. | $O(1)$ random access. |

---

## 🗄️ 6. Database Schema Design

The application data uses six relational tables; an additional `sessions` table
stores hashed login-token digests for serverless-safe sessions:

1. **`users`**: Resident and administrator credentials. Passwords are encrypted using **PBKDF2-HMAC-SHA256** with unique salts.
   - `id`, `full_name`, `mobile` (UNIQUE), `email` (UNIQUE), `village`, `address`, `password_hash`, `role`, `created_at`.
2. **`departments`**: Gram Panchayat administrative departments.
   - `id`, `name` (UNIQUE), `contact`, `description`.
3. **`resources`**: Village infrastructure assets.
   - `id`, `name`, `category`, `location`, `contact`, `availability`, `description`, `created_at`.
4. **`grievances`**: Citizen complaints filed.
   - `id`, `grievance_code` (UNIQUE, format `GRV-2026-XXXX`), `user_id` (FK), `category`, `subject`, `description`, `location`, `priority`, `status`, `department_id` (FK), `created_at`, `updated_at`.
5. **`announcements`**: Public development notices.
   - `id`, `title`, `description`, `announcement_date`, `created_at`.
6. **`grievance_updates`**: Step-by-step audit trail for vertical status timeline.
   - `id`, `grievance_id` (FK), `status`, `comment`, `updated_by` (FK), `created_at`.

---

## 🌐 7. REST API Endpoints Overview

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/register` | Register a new villager | Public |
| `POST` | `/api/login` | Authenticate using email, User ID, or mobile & password | Public |
| `POST` | `/api/logout` | Terminate session and clear cookie | Public |
| `GET` | `/api/session` | Fetch active user session information | Public |
| `GET` | `/api/resources` | List all resources (optional `?category=`) | Public |
| `GET` | `/api/resources/search?q=` | Search resources using Python search algorithm | Public |
| `POST` | `/api/resources` | Create a new resource record | Admin |
| `PUT` | `/api/resources/{id}` | Update existing resource | Admin |
| `DELETE` | `/api/resources/{id}` | Delete a resource record | Admin |
| `POST` | `/api/grievances` | Submit a new grievance (generates `GRV-2026-XXXX`) | Villager |
| `GET` | `/api/grievances/{id_or_code}`| Fetch grievance details and timeline updates | Public / Villager / Admin |
| `GET` | `/api/grievances/user` | Fetch grievances of currently logged-in villager | Villager |
| `GET` | `/api/admin/grievances` | Fetch grievances with `?view=priority` or `?view=fifo` | Admin |
| `PUT` | `/api/grievances/{id}` | Update status, assign department, upgrade priority | Admin |
| `POST` | `/api/grievances/{id}/updates`| Append comment to grievance timeline | Admin |
| `GET` | `/api/departments` | List all village departments | Public |
| `POST` | `/api/departments` | Add a new department | Admin |
| `GET` | `/api/announcements` | List public village notices | Public |
| `POST` | `/api/announcements` | Post a new announcement | Admin |
| `GET` | `/api/admin/statistics` | Retrieve dashboard aggregate counts | Admin |
| `GET` | `/api/admin/users` | List registered residents and admins | Admin |
| `GET` | `/api/admin/reports` | Get breakdown by category, priority, status, dept | Admin |

---

## 🚀 8. Installation & Quickstart

### Step 1: Open Terminal
Open PowerShell, Command Prompt, or VS Code terminal in the project directory:
```bash
cd Village_Resource_Grievance_System
```

### Step 2: Initialize Database
Run the automated initialization script. It applies the SQLite schema and safe
user-table migration, initializes village resources, and loads sample records:
```bash
python setup_database.py
```

### Step 3: Start the Backend Server
Start the multi-threaded standard library HTTP server:
```bash
python server.py
```

### Step 4: Open in Web Browser
Open your browser (Chrome, Edge, Firefox) and navigate to:
```
http://localhost:8000
```

## Deploying to Vercel

This repository includes `vercel.json` and `api/index.py` so the existing Python
HTTP handler can run as a Vercel Python function.

### Deploy from GitHub

1. Push this repository to GitHub.
2. Open [vercel.com](https://vercel.com) and select **Add New Project**.
3. Import the GitHub repository.
4. Keep the project root as the repository root.
5. Complete the persistent database setup below, set the server-side database
   variables in Vercel, then deploy.

### Deploy with the Vercel CLI

```bash
npm install -g vercel
vercel login
vercel
vercel --prod
```

### Persistent MySQL on Vercel

Vercel functions cannot reach a MySQL server running on your laptop, and their
`/tmp` filesystem is temporary. The Vercel adapter therefore rejects SQLite-only
production configuration with HTTP 503 rather than creating a fresh database that
looks like a successful deployment. Production login sessions are stored in MySQL;
only a SHA-256 digest of each random session token is stored.

**Recommended provider:** Aiven for MySQL, using a supported service plan with
TLS, backups/retention appropriate for your data, and IP filtering. Availability,
backup retention, and recovery guarantees depend on the selected plan; do not
assume an always-on guarantee. See [Aiven's MySQL setup guide](https://aiven.io/docs/products/mysql/get-started).

Vercel uses dynamic outbound IPs by default. Before enabling production access,
check the project plan and region. Vercel Static IPs are available on Pro and
Enterprise plans; Secure Compute with private networking is an Enterprise option.
Restrict the database network rule to the Vercel egress IPs, require TLS, and use
a dedicated database user. If your plan has no fixed/restricted egress, do not
allow `0.0.0.0/0`; use an eligible Vercel network option or host the API and
database in a network where private access is available. See [Vercel Static IPs](https://vercel.com/docs/networking/static-ips)
and [Secure Compute](https://vercel.com/docs/networking/secure-compute).

#### Back up and migrate SQLite data

The migration script never deletes or overwrites source data and refuses to import
into a target that already contains application records. First make a separate
backup and validate it:

```bash
python3 - <<'PY'
import sqlite3
from pathlib import Path
source = Path("village_system.db")
backup = Path("village_system.pre-mysql.sqlite3")
with sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True) as original, sqlite3.connect(backup) as copy:
    original.backup(copy)
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    for (table,) in original.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        original_count = original.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()
        backup_count = copy.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()
        assert original_count == backup_count
print("Backup verified:", backup)
PY
```

Install the project requirements and create an empty MySQL database. For local
development and the one-time migration, create a private environment file from
the template:

```bash
cp .env.example .env
```

Edit `.env` and set the connection values below. The app loads this file
automatically; it does not override variables already exported by your shell.
Leave the MySQL values empty to continue using SQLite locally. Restart the app
or migration command after changing `.env`.

Configure the same values as **server-side** environment variables in Vercel
Production (and Preview only if wanted); Vercel does not receive your local
`.env` file:

- `GRAMSEVA_DB_HOST`
- `GRAMSEVA_DB_PORT` (defaults to `3306`)
- `GRAMSEVA_DB_NAME`
- `GRAMSEVA_DB_USER`
- `GRAMSEVA_DB_PASSWORD`
- `GRAMSEVA_DB_SSL_CA` (CA certificate PEM text or a readable certificate path)

Use a migration account with schema/data privileges for the one-time import, then
use a separate least-privilege runtime account in Vercel with only the required
`SELECT`, `INSERT`, `UPDATE`, and `DELETE` permissions. Obtain the CA certificate
from the provider. The backend verifies both the TLS certificate and server name.
Do not put these values in frontend files, source control, or a committed `.env`.
The repository ignores `.env`; commit only `.env.example`.

After making and validating the backup, run a read-only count check:

```bash
python migrate_to_mysql.py --source /absolute/path/to/village_system.pre-mysql.sqlite3
```

Review the counts, confirm the MySQL target is empty, then explicitly apply:

```bash
python migrate_to_mysql.py --source /absolute/path/to/village_system.pre-mysql.sqlite3 --apply
```

The importer creates the MySQL schema, preserves IDs, account roles, password
hashes, grievances, resources, departments, announcements, and update timelines.
It compares per-table row counts and content fingerprints before committing and
reports only counts/results (not personal records or password hashes). Keep the
SQLite source and backup unchanged until you have independently checked the
production site and database. Never point the importer at a non-empty target.

#### Vercel deployment

1. Create the managed MySQL service and database; configure TLS and network
    restrictions before importing.
2. Enable Vercel Static IPs or Secure Compute if needed, then allowlist only the
    applicable outbound addresses at the database provider.
3. Back up and migrate from the SQLite source as above; verify all six application
    tables and their imported records.
4. In Vercel **Project → Settings → Environment Variables**, set the six
    `GRAMSEVA_DB_*` names above as sensitive server-side values; do not use any
    `NEXT_PUBLIC_`/frontend-exposed prefix.
5. Redeploy. If configuration, TLS, network access, or required MySQL tables are
    missing, the API logs a secret-free diagnostic and returns HTTP 503, rather
    than silently using ephemeral SQLite.
6. Test registration, email/User ID/mobile login, logout, both role dashboards,
    grievance submission/tracking/status updates, resource administration, and
    reports on the deployed site. Test mobile and desktop layouts, and confirm
    registrations and submissions persist after a new deployment.

---

## 🔐 10. Accounts and administrator setup

Residents can create accounts from **Register as Villager**. Each registration
requires a unique User ID, email address, and 10-digit mobile number. New
registrations always receive the `villager` role; the role selector on the login
page does not grant privileges.

Administrator accounts are not created by public registration. Configure all
of the following environment variables before running `python setup_database.py`
to create an initial administrator or rotate the configured administrator in an
existing database:

- `GRAMSEVA_ADMIN_USERNAME`
- `GRAMSEVA_ADMIN_NAME`
- `GRAMSEVA_ADMIN_EMAIL`
- `GRAMSEVA_ADMIN_MOBILE`
- `GRAMSEVA_ADMIN_PASSWORD` (at least 8 characters)

Supply the administrator password through the deployment's secret manager; do
not put it in source control or frontend code. Existing administrator records in
an older database are retained; when the configured username, email, and mobile
identify an existing administrator, setup updates that account's profile and
password hash from the configured values. Existing sample villager records
remain only as sample data; they are not required for public registration.

The migration adds User IDs to existing accounts and creates unique indexes for
User IDs and case-insensitive email addresses. Back up `village_system.db` before
upgrading, then run `python setup_database.py` once; existing user and grievance
records are retained. Set `GRAMSEVA_DATABASE_PATH` first if the database is not
at the default project path.

The application keeps the existing PBKDF2-HMAC-SHA256 format across registration
and login. Public registrations always get the `villager` role, and login checks
that the selected role matches the stored account role.

---

## 🧪 11. Automated Testing

To run the automated backend test suite covering database schema, password hashing,
registration and login by all supported identifiers, duplicate rejection, role
separation, FIFO Queue, Min-Heap Priority Queue, searching, and sorting:

```bash
python test_backend.py
```

Expected output:
```
Ran 14 tests in approximately 1s
OK
```

---

## 🔄 12. Grievance Redressal Lifecycle

```
Villager Files Complaint
         │
         ▼
System Assigns Code (GRV-2026-XXXX) & Status: "Submitted"
         │
         ▼
Enters Admin FIFO & Priority Queue (Min-Heap triage)
         │
         ▼
Admin Inspects & Verifies -> Status: "Verified"
         │
         ▼
Department Assigned (Water/Power/PWD/Health) -> Status: "Assigned"
         │
         ▼
Field Crew Dispatched -> Status: "In Progress"
         │
         ▼
Issue Resolved & Confirmed -> Status: "Resolved"
(Audit trail with officer remarks recorded at every step)
```

---

## 🛠️ 13. Troubleshooting & FAQ

- **Port 8000 already in use?**
  You can modify `PORT = 8000` in `config.py` to another port such as `8080` or `5000`.
- **Database reset:**
  To reset the database to fresh factory seed data, simply delete `village_system.db` and run `python setup_database.py`.
- **Browser caching:**
  The server sets `Cache-Control: no-cache, no-store, must-revalidate` for development convenience. If you make frontend HTML/CSS adjustments, a simple browser refresh (`Ctrl+F5`) displays changes immediately.
