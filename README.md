# Village Resources and Grievance Management System (GramSeva)
**A Full-Stack College Capstone Project**

---

## 📌 1. Project Overview

The **Village Resources and Grievance Management System (GramSeva)** is a digital governance platform designed for rural Gram Panchayats. It enables village residents to easily discover public resources, search services, submit grievances, and track resolution timelines in real time. For administrators, it provides a centralized console to triage complaints using Priority Queues, assign responsible municipal departments, manage public facilities, broadcast announcements, and monitor civic analytics.

### Key Goals:
- Connect villagers with essential village amenities (health clinics, schools, water supply, public libraries, electricity transformers).
- Transparent, algorithmic grievance redressal with automated tracking codes (`GRV-YYYY-XXXX`).
- Multi-language inclusivity with instantaneous support for **English**, **मराठी (Marathi)**, and **हिन्दी (Hindi)**.
- **100% Python Standard Library backend** with zero external dependencies (no Flask, no Django, no React).

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
│  In-Memory Session Store      │  • FIFO GrievanceQueue          │
│  Role-Based Access Control    │  • Heapq GrievancePriorityQueue │
│                               │  • Multi-attribute Search & Sort│
└───────────────────────────────┴────────────────┬────────────────┘
                                                 │ Parameterized SQL
┌────────────────────────────────────────────────▼────────────────┐
│                       SQLite Database                           │
│   users, resources, departments, grievances, announcements,     │
│   grievance_updates                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 3. Technology Stack

- **Frontend:** HTML5, CSS3 (Modern Responsive Flexbox/Grid, CSS Variables), Vanilla JavaScript (ES6+).
- **Backend:** Python 3.8+ utilizing **strictly the Python Standard Library**:
  - `http.server` & `socketserver` (Multi-threaded HTTP Server)
  - `sqlite3` (ACID Relational Database Storage)
  - `hashlib` (PBKDF2-HMAC-SHA256 Password Hashing)
  - `heapq` (Min-Heap Priority Queue)
  - `collections.deque` (FIFO Grievance Intake Queue)
  - `json` & `urllib.parse` (API Serialization & Routing)
  - `unittest` (Automated backend verification)
- **Database:** SQLite 3 (`village_system.db`).
- **External Dependencies:** **ZERO (`0`) external pip dependencies required.**

---

## 📂 4. Project Folder Structure

```
Village_Resource_Grievance_System/
│
├── server.py                   # Multi-threaded HTTP Server & REST API Dispatcher
├── database.py                 # SQLite database query and persistence layer
├── config.py                   # System constants, ports, and priority rankings
├── requirements.txt            # Zero-dependency specification file
├── README.md                   # Complete documentation and setup guide
├── setup_database.py           # Database initialisation and realistic seeding script
├── test_backend.py             # Unittest test suite for backend, DB, queues, and search
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

The SQLite database comprises 6 relational tables with foreign keys and indexes:

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
| `POST` | `/api/login` | Authenticate using email/mobile & password | Public |
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
Run the automated initialization script. This sets up the SQLite schema, indexes, demo accounts, and sample data:
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

---

## 🔑 9. Demo Login Credentials

For testing and presentation evaluation, the following demo accounts are pre-configured:

### 👑 Administrator Account
- **Role:** `Admin`
- **Email:** `admin@village.local`
- **Mobile:** `9876543210`
- **Password:** `Admin@123`
- *Access:* Full administrative dashboard (`admin.html`), Priority Queue view, FIFO Queue view, status updates, department assignments, resource/announcement CRUD.

### 🧑‍🌾 Villager / Citizen Account 1
- **Role:** `Villager`
- **Email:** `ramesh@village.local`
- **Mobile:** `9822011223`
- **Password:** `Villager@123`
- *Access:* Villager dashboard (`dashboard.html`), file grievances, track personal issues.

### 🧑‍🌾 Villager / Citizen Account 2
- **Role:** `Villager`
- **Email:** `sunita@village.local`
- **Mobile:** `9822011224`
- **Password:** `Villager@123`

---

## 🧪 10. Automated Testing

To run the automated backend test suite covering database schema, password hashing, authentication, FIFO Queue, Min-Heap Priority Queue, searching, and sorting:

```bash
python test_backend.py
```

Expected output:
```
Ran 12 tests in 0.39s
OK
```

---

## 🔄 11. Grievance Redressal Lifecycle

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

## 🛠️ 12. Troubleshooting & FAQ

- **Port 8000 already in use?**
  You can modify `PORT = 8000` in `config.py` to another port such as `8080` or `5000`.
- **Database reset:**
  To reset the database to fresh factory seed data, simply delete `village_system.db` and run `python setup_database.py`.
- **Browser caching:**
  The server sets `Cache-Control: no-cache, no-store, must-revalidate` for development convenience. If you make frontend HTML/CSS adjustments, a simple browser refresh (`Ctrl+F5`) displays changes immediately.
