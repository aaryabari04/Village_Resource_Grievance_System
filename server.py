"""
Main HTTP Server and REST API Dispatcher for Village Resources & Grievance Management System.
Built 100% using Python's standard library http.server and socketserver.
NO FLASK OR DJANGO USED.
"""

import os
import sys
import json
import time
import secrets
import mimetypes
import threading
from pathlib import Path
from http import cookies
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs, unquote

# Add parent directory to module search path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

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

# Thread-safe in-memory session store
# Schema: { session_token: { "user_id": int, "role": str, "expires": float } }
SESSIONS = {}
SESSION_LOCK = threading.Lock()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server handling concurrent requests cleanly."""
    daemon_threads = True
    allow_reuse_address = True


class VillageAppHandler(BaseHTTPRequestHandler):
    """Request handler implementing REST API endpoints and static file delivery."""

    server_version = "VillageCivicServer/1.0"

    # =====================================================================
    # RESPONSE HELPERS
    # =====================================================================

    def send_json(self, data, status: int = 200, set_cookies: list = None):
        """Sends a JSON response with appropriate headers and status code."""
        response_bytes = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token")
        
        if set_cookies:
            for c in set_cookies:
                self.send_header("Set-Cookie", c)

        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_json(self, message: str, status: int = 400, details: dict = None):
        """Sends a structured JSON error response."""
        payload = {
            "success": False,
            "error": message,
            "status": status
        }
        if details:
            payload["details"] = details
        self.send_json(payload, status=status)

    def parse_request_body(self) -> dict:
        """Reads and parses JSON body from request."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            raw_body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_body)
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON payload in request body")
        except Exception as e:
            raise ValueError(f"Unable to read request payload: {str(e)}")

    # =====================================================================
    # SESSION & AUTHENTICATION HELPERS
    # =====================================================================

    def get_session_token(self) -> str:
        """Retrieves session token from Cookie or custom request headers."""
        # 1. Check custom Header
        token = self.headers.get("X-Session-Token")
        if token:
            return token.strip()

        # 2. Check Authorization Header: Bearer <token>
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1].strip()

        # 3. Check Cookie
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            c = cookies.SimpleCookie()
            try:
                c.load(cookie_header)
                if config.SESSION_COOKIE_NAME in c:
                    return c[config.SESSION_COOKIE_NAME].value
            except Exception:
                pass

        return ""

    def get_current_user(self) -> dict:
        """
        Validates session token and returns user profile dict if active.
        Returns None if not authenticated.
        """
        token = self.get_session_token()
        if not token:
            return None

        with SESSION_LOCK:
            session_info = SESSIONS.get(token)
            if not session_info:
                return None

            # Check expiration
            if time.time() > session_info.get("expires", 0):
                del SESSIONS[token]
                return None

            user_id = session_info.get("user_id")

        return database.get_user_by_id(user_id)

    # =====================================================================
    # HTTP METHODS DISPATCHER
    # =====================================================================

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        """Dispatches GET requests to API routes or static file handler."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        try:
            if path.startswith("/api/"):
                self.handle_api_get(path, query_params)
            else:
                self.handle_static_files(path)
        except Exception as e:
            print(f"[ERROR] Exception in GET {path}: {e}", file=sys.stderr)
            self.send_error_json("An unexpected internal server error occurred", status=500)

    def do_POST(self):
        """Dispatches POST requests to API routes."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        try:
            if path.startswith("/api/"):
                body = self.parse_request_body()
                self.handle_api_post(path, body)
            else:
                self.send_error_json("Method Not Allowed for static assets", status=405)
        except ValueError as ve:
            self.send_error_json(str(ve), status=400)
        except Exception as e:
            print(f"[ERROR] Exception in POST {path}: {e}", file=sys.stderr)
            self.send_error_json("An unexpected internal server error occurred", status=500)

    def do_PUT(self):
        """Dispatches PUT requests to API routes."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        try:
            if path.startswith("/api/"):
                body = self.parse_request_body()
                self.handle_api_put(path, body)
            else:
                self.send_error_json("Method Not Allowed", status=405)
        except ValueError as ve:
            self.send_error_json(str(ve), status=400)
        except Exception as e:
            print(f"[ERROR] Exception in PUT {path}: {e}", file=sys.stderr)
            self.send_error_json("An unexpected internal server error occurred", status=500)

    def do_DELETE(self):
        """Dispatches DELETE requests to API routes."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        try:
            if path.startswith("/api/"):
                self.handle_api_delete(path)
            else:
                self.send_error_json("Method Not Allowed", status=405)
        except Exception as e:
            print(f"[ERROR] Exception in DELETE {path}: {e}", file=sys.stderr)
            self.send_error_json("An unexpected internal server error occurred", status=500)

    # =====================================================================
    # STATIC FILE HANDLER
    # =====================================================================

    def handle_static_files(self, path: str):
        """Serves HTML, CSS, JavaScript, and asset files safely."""
        # Normalize index and root paths
        if path in ("", "/", "/index", "/index.html"):
            target_file = config.FRONTEND_DIR / "index.html"
        elif path.startswith("/css/"):
            rel_name = path[5:]
            target_file = config.CSS_DIR / rel_name
        elif path.startswith("/js/"):
            rel_name = path[4:]
            target_file = config.JS_DIR / rel_name
        elif path.startswith("/assets/"):
            rel_name = path[8:]
            target_file = config.ASSETS_DIR / rel_name
        else:
            # Check if file exists in frontend/ directory (e.g. /login.html, /dashboard.html)
            clean_name = path.lstrip("/")
            if not clean_name.endswith(".html") and "." not in clean_name:
                clean_name += ".html"
            target_file = config.FRONTEND_DIR / clean_name

        # Ensure target file exists and prevent path traversal
        try:
            target_file = target_file.resolve()
            if not target_file.is_file():
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<h1>404 Not Found</h1><p>The requested page or file does not exist.</p>")
                return

            # Prevent directory traversal outside of project root
            if not str(target_file).startswith(str(config.BASE_DIR)):
                self.send_response(403)
                self.end_headers()
                return

            # Determine content type
            mime_type, _ = mimetypes.guess_type(str(target_file))
            if not mime_type:
                mime_type = "application/octet-stream"
            if mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json"):
                mime_type += "; charset=utf-8"

            file_size = target_file.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()

            with open(target_file, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

        except Exception as e:
            print(f"[ERROR] Static file error for {path}: {e}", file=sys.stderr)
            self.send_response(500)
            self.end_headers()

    # =====================================================================
    # API: GET HANDLER
    # =====================================================================

    def handle_api_get(self, path: str, query_params: dict):
        user = self.get_current_user()

        # -------------------------------------------------------------
        # 1. Session Information
        # -------------------------------------------------------------
        if path == "/api/session":
            if user:
                self.send_json({
                    "authenticated": True,
                    "user": user
                })
            else:
                self.send_json({
                    "authenticated": False,
                    "user": None
                })
            return

        # -------------------------------------------------------------
        # 2. Resources Catalog & Search
        # -------------------------------------------------------------
        if path == "/api/resources":
            resources = database.get_all_resources()
            category = query_params.get("category", [None])[0]
            if category and category.lower() != "all":
                resources = [r for r in resources if r.get("category", "").lower() == category.lower()]
            self.send_json({"success": True, "count": len(resources), "resources": resources})
            return

        if path == "/api/resources/search":
            q = query_params.get("q", [""])[0]
            all_res = database.get_all_resources()
            # ACTUALLY USE Search Algorithm from data_structures/search_sort.py
            matched = search_resources(all_res, q)
            self.send_json({
                "success": True,
                "query": q,
                "count": len(matched),
                "resources": matched
            })
            return

        # -------------------------------------------------------------
        # 3. Departments
        # -------------------------------------------------------------
        if path == "/api/departments":
            depts = database.get_all_departments()
            self.send_json({"success": True, "departments": depts})
            return

        # -------------------------------------------------------------
        # 4. Announcements
        # -------------------------------------------------------------
        if path == "/api/announcements":
            announcements = database.get_all_announcements()
            self.send_json({"success": True, "announcements": announcements})
            return

        # -------------------------------------------------------------
        # 5. Grievances for Logged-In User
        # -------------------------------------------------------------
        if path == "/api/grievances/user":
            if not user:
                self.send_error_json("Authentication required to view your grievances", status=401)
                return
            user_grievances = database.get_grievances_by_user(user["id"])
            self.send_json({"success": True, "grievances": user_grievances})
            return

        # -------------------------------------------------------------
        # 6. Admin Endpoints
        # -------------------------------------------------------------
        if path == "/api/admin/statistics":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return
            stats = database.get_admin_statistics()
            self.send_json({"success": True, "statistics": stats})
            return

        if path == "/api/admin/reports":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return
            reports = database.get_admin_reports()
            self.send_json({"success": True, "reports": reports})
            return

        if path == "/api/admin/users":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return
            users = database.get_all_users()
            self.send_json({"success": True, "users": users})
            return

        if path == "/api/admin/resources":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return
            resources = database.get_all_resources()
            self.send_json({"success": True, "resources": resources})
            return

        # Admin Grievances List (with Priority Queue and FIFO Queue integration)
        if path in ("/api/admin/grievances", "/api/grievances"):
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return

            all_grievances = database.get_all_grievances()
            view_mode = query_params.get("view", ["default"])[0].lower()
            search_query = query_params.get("q", [""])[0]
            filter_status = query_params.get("status", [""])[0]
            filter_priority = query_params.get("priority", [""])[0]
            sort_by = query_params.get("sort", [""])[0]

            # 1. Search filter using data structures search algorithm
            if search_query:
                all_grievances = search_grievances(all_grievances, search_query)

            # 2. Filter by status / priority
            if filter_status and filter_status != "All":
                all_grievances = [g for g in all_grievances if g["status"].lower() == filter_status.lower()]
            if filter_priority and filter_priority != "All":
                all_grievances = [g for g in all_grievances if g["priority"].lower() == filter_priority.lower()]

            # 3. View Mode using Data Structures:
            #    a) Priority Queue mode (Emergency -> High -> Medium -> Low)
            #    b) FIFO Queue mode (Order of submission)
            #    c) Custom Sorts
            if view_mode == "priority":
                # ACTUALLY USE PRIORITY QUEUE (heapq implementation)
                pq = GrievancePriorityQueue()
                for g in all_grievances:
                    pq.push(g)
                processed_grievances = pq.to_sorted_list()
                mode_used = "Priority Queue (Heapq: Emergency > High > Medium > Low)"
            elif view_mode == "fifo":
                # ACTUALLY USE FIFO QUEUE
                # Sort initially by ID/timestamp ascending to emulate chronological intake
                raw_fifo = sorted(all_grievances, key=lambda x: x["id"])
                queue = GrievanceQueue(raw_fifo)
                processed_grievances = queue.to_list()
                mode_used = "FIFO Queue (Standard sequential order)"
            elif sort_by == "priority":
                processed_grievances = sort_grievances_by_priority(all_grievances)
                mode_used = "Sorted by Priority"
            elif sort_by == "status":
                processed_grievances = sort_grievances_by_status(all_grievances)
                mode_used = "Sorted by Workflow Status"
            elif sort_by == "date_asc":
                processed_grievances = sort_grievances_by_date(all_grievances, reverse=False)
                mode_used = "Sorted by Date (Oldest First)"
            else:
                # Default: Newest first
                processed_grievances = sort_grievances_by_date(all_grievances, reverse=True)
                mode_used = "Sorted by Date (Newest First)"

            self.send_json({
                "success": True,
                "view": view_mode,
                "data_structure_mode": mode_used,
                "count": len(processed_grievances),
                "grievances": processed_grievances
            })
            return

        # -------------------------------------------------------------
        # 7. Single Grievance Details & Timeline (/api/grievances/{id_or_code})
        # -------------------------------------------------------------
        if path.startswith("/api/grievances/"):
            identifier = path[len("/api/grievances/"):].strip()
            # Identifier can be integer ID or string grievance code like GRV-2026-0001
            grievance = None
            if identifier.isdigit():
                grievance = database.get_grievance_by_id(int(identifier))
            if not grievance:
                grievance = database.get_grievance_by_code(identifier)

            if not grievance:
                self.send_error_json("Grievance not found with specified ID or Code", status=404)
                return

            # Public tracking is permitted by code; private ID access requires ownership or admin
            if not user and not identifier.startswith("GRV-"):
                self.send_error_json("Authentication required", status=401)
                return

            if user and user["role"] != "admin" and grievance["user_id"] != user["id"]:
                # Villager attempting to view another's grievance by numeric ID
                if not identifier.startswith("GRV-"):
                    self.send_error_json("You are not authorized to view this grievance", status=403)
                    return

            updates = database.get_grievance_updates(grievance["id"])
            self.send_json({
                "success": True,
                "grievance": grievance,
                "timeline": updates
            })
            return

        # Fallback 404 for unknown API routes
        self.send_error_json(f"Endpoint GET {path} not found", status=404)

    # =====================================================================
    # API: POST HANDLER
    # =====================================================================

    def handle_api_post(self, path: str, body: dict):
        user = self.get_current_user()

        # -------------------------------------------------------------
        # 1. User Registration
        # -------------------------------------------------------------
        if path == "/api/register":
            full_name = body.get("full_name", "").strip()
            mobile = body.get("mobile", "").strip()
            email = body.get("email", "").strip()
            village = body.get("village", "").strip()
            address = body.get("address", "").strip()
            password = body.get("password", "")
            confirm_password = body.get("confirm_password", "")

            # Validation
            if not full_name or not mobile or not village or not password:
                self.send_error_json("Full Name, Mobile, Village, and Password are required fields.", status=400)
                return

            if len(mobile) < 10 or not mobile.replace("+", "").isdigit():
                self.send_error_json("Please provide a valid 10-digit mobile number.", status=400)
                return

            if confirm_password and password != confirm_password:
                self.send_error_json("Passwords do not match.", status=400)
                return

            if len(password) < 6:
                self.send_error_json("Password must be at least 6 characters long.", status=400)
                return

            # Duplicate check
            existing = database.get_user_by_login(mobile)
            if not existing and email:
                existing = database.get_user_by_login(email)
            if existing:
                self.send_error_json("An account with this mobile number or email already exists.", status=400)
                return

            try:
                new_user_id = database.create_user(
                    full_name=full_name,
                    mobile=mobile,
                    email=email,
                    village=village,
                    address=address,
                    password=password,
                    role="villager"
                )
                self.send_json({
                    "success": True,
                    "message": "Registration successful! You may now log in.",
                    "user_id": new_user_id
                }, status=201)
            except Exception as e:
                self.send_error_json(f"Registration error: {str(e)}", status=500)
            return

        # -------------------------------------------------------------
        # 2. User Login
        # -------------------------------------------------------------
        if path == "/api/login":
            identifier = body.get("identifier", "").strip()
            password = body.get("password", "")
            requested_role = body.get("role", "villager").strip().lower()

            if not identifier or not password:
                self.send_error_json("Please provide both email/mobile and password.", status=400)
                return

            account = database.get_user_by_login(identifier)
            if not account or not database.verify_password(password, account["password_hash"]):
                self.send_error_json("Invalid credentials. Please verify your email/mobile and password.", status=401)
                return

            # Verify role requirement
            if requested_role == "admin" and account["role"] != "admin":
                self.send_error_json("Access denied: You do not possess administrative privileges.", status=403)
                return

            # Generate session token
            token = secrets.token_hex(32)
            expires_at = time.time() + config.SESSION_LIFETIME_SECONDS

            with SESSION_LOCK:
                SESSIONS[token] = {
                    "user_id": account["id"],
                    "role": account["role"],
                    "expires": expires_at
                }

            # Prepare user object without password hash
            user_safe = {
                "id": account["id"],
                "full_name": account["full_name"],
                "mobile": account["mobile"],
                "email": account["email"],
                "village": account["village"],
                "address": account["address"],
                "role": account["role"]
            }

            cookie_str = f"{config.SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_LIFETIME_SECONDS}"

            self.send_json({
                "success": True,
                "message": "Login successful",
                "token": token,
                "user": user_safe
            }, status=200, set_cookies=[cookie_str])
            return

        # -------------------------------------------------------------
        # 3. User Logout
        # -------------------------------------------------------------
        if path == "/api/logout":
            token = self.get_session_token()
            if token:
                with SESSION_LOCK:
                    SESSIONS.pop(token, None)

            cookie_clear = f"{config.SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            self.send_json({
                "success": True,
                "message": "Successfully logged out"
            }, set_cookies=[cookie_clear])
            return

        # -------------------------------------------------------------
        # 4. Submit Grievance
        # -------------------------------------------------------------
        if path == "/api/grievances":
            if not user:
                self.send_error_json("You must be logged in to submit a grievance.", status=401)
                return

            category = body.get("category", "").strip()
            subject = body.get("subject", "").strip()
            description = body.get("description", "").strip()
            location = body.get("location", "").strip()
            priority = body.get("priority", "Medium").strip()

            if not category or not subject or not description or not location:
                self.send_error_json("Category, Subject, Description, and Location are mandatory fields.", status=400)
                return

            if priority not in config.ALLOWED_PRIORITIES:
                priority = "Medium"

            created_grv = database.create_grievance(
                user_id=user["id"],
                category=category,
                subject=subject,
                description=description,
                location=location,
                priority=priority
            )

            self.send_json({
                "success": True,
                "message": "Grievance submitted successfully.",
                "grievance_code": created_grv["grievance_code"],
                "grievance": created_grv
            }, status=201)
            return

        # -------------------------------------------------------------
        # 5. Add Grievance Update Comment (Admin or Grievance Timeline)
        # -------------------------------------------------------------
        if path.startswith("/api/grievances/") and path.endswith("/updates"):
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required to append status updates", status=403)
                return

            parts = path.strip("/").split("/")
            grv_id_str = parts[2]
            if not grv_id_str.isdigit():
                self.send_error_json("Invalid grievance ID parameter", status=400)
                return

            grv_id = int(grv_id_str)
            status_val = body.get("status", "").strip()
            comment_val = body.get("comment", "").strip()

            if not status_val or not comment_val:
                self.send_error_json("Both status and comment are required.", status=400)
                return

            database.add_grievance_update(
                grievance_id=grv_id,
                status=status_val,
                comment=comment_val,
                updated_by=user["id"]
            )
            # Update grievance status in main record
            database.update_grievance_status_and_assignment(
                grievance_id=grv_id,
                status=status_val,
                comment=comment_val,
                updated_by=user["id"]
            )

            self.send_json({
                "success": True,
                "message": "Update logged successfully"
            }, status=201)
            return

        # -------------------------------------------------------------
        # 6. Add Resource (Admin only)
        # -------------------------------------------------------------
        if path == "/api/resources":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return

            name = body.get("name", "").strip()
            category = body.get("category", "").strip()
            location = body.get("location", "").strip()
            contact = body.get("contact", "").strip()
            availability = body.get("availability", "").strip()
            description = body.get("description", "").strip()

            if not name or not category:
                self.send_error_json("Resource Name and Category are required.", status=400)
                return

            new_id = database.create_resource(name, category, location, contact, availability, description)
            self.send_json({
                "success": True,
                "message": "Resource created successfully",
                "resource_id": new_id
            }, status=201)
            return

        # -------------------------------------------------------------
        # 7. Add Department (Admin only)
        # -------------------------------------------------------------
        if path == "/api/departments":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return

            name = body.get("name", "").strip()
            contact = body.get("contact", "").strip()
            description = body.get("description", "").strip()

            if not name:
                self.send_error_json("Department Name is required.", status=400)
                return

            new_id = database.create_department(name, contact, description)
            self.send_json({
                "success": True,
                "message": "Department created successfully",
                "department_id": new_id
            }, status=201)
            return

        # -------------------------------------------------------------
        # 8. Add Announcement (Admin only)
        # -------------------------------------------------------------
        if path == "/api/announcements":
            if not user or user["role"] != "admin":
                self.send_error_json("Admin privileges required", status=403)
                return

            title = body.get("title", "").strip()
            description = body.get("description", "").strip()
            announcement_date = body.get("announcement_date", "").strip()

            if not title or not description or not announcement_date:
                self.send_error_json("Title, Description, and Announcement Date are required.", status=400)
                return

            new_id = database.create_announcement(title, description, announcement_date)
            self.send_json({
                "success": True,
                "message": "Announcement posted successfully",
                "announcement_id": new_id
            }, status=201)
            return

        self.send_error_json(f"Endpoint POST {path} not found", status=404)

    # =====================================================================
    # API: PUT HANDLER
    # =====================================================================

    def handle_api_put(self, path: str, body: dict):
        user = self.get_current_user()
        if not user or user["role"] != "admin":
            self.send_error_json("Admin privileges required", status=403)
            return

        # 1. Update Grievance (/api/grievances/{id})
        if path.startswith("/api/grievances/"):
            grv_id_str = path[len("/api/grievances/"):].strip()
            if not grv_id_str.isdigit():
                self.send_error_json("Invalid grievance ID parameter", status=400)
                return

            grv_id = int(grv_id_str)
            status_val = body.get("status")
            priority_val = body.get("priority")
            dept_id = body.get("department_id")
            comment_val = body.get("comment", "")

            if status_val and status_val not in config.ALLOWED_STATUSES:
                self.send_error_json(f"Invalid status: {status_val}", status=400)
                return

            if priority_val and priority_val not in config.ALLOWED_PRIORITIES:
                self.send_error_json(f"Invalid priority: {priority_val}", status=400)
                return

            success = database.update_grievance_status_and_assignment(
                grievance_id=grv_id,
                status=status_val,
                priority=priority_val,
                department_id=dept_id,
                comment=comment_val,
                updated_by=user["id"]
            )

            if success:
                self.send_json({
                    "success": True,
                    "message": "Grievance successfully updated"
                })
            else:
                self.send_error_json("Grievance not found", status=404)
            return

        # 2. Update Resource (/api/resources/{id})
        if path.startswith("/api/resources/"):
            res_id_str = path[len("/api/resources/"):].strip()
            if not res_id_str.isdigit():
                self.send_error_json("Invalid resource ID", status=400)
                return

            res_id = int(res_id_str)
            database.update_resource(
                resource_id=res_id,
                name=body.get("name", ""),
                category=body.get("category", ""),
                location=body.get("location", ""),
                contact=body.get("contact", ""),
                availability=body.get("availability", ""),
                description=body.get("description", "")
            )
            self.send_json({"success": True, "message": "Resource updated successfully"})
            return

        # 3. Update Department (/api/departments/{id})
        if path.startswith("/api/departments/"):
            dept_id_str = path[len("/api/departments/"):].strip()
            if not dept_id_str.isdigit():
                self.send_error_json("Invalid department ID", status=400)
                return

            dept_id = int(dept_id_str)
            database.update_department(
                dept_id=dept_id,
                name=body.get("name", ""),
                contact=body.get("contact", ""),
                description=body.get("description", "")
            )
            self.send_json({"success": True, "message": "Department updated successfully"})
            return

        # 4. Update Announcement (/api/announcements/{id})
        if path.startswith("/api/announcements/"):
            ann_id_str = path[len("/api/announcements/"):].strip()
            if not ann_id_str.isdigit():
                self.send_error_json("Invalid announcement ID", status=400)
                return

            ann_id = int(ann_id_str)
            database.update_announcement(
                announcement_id=ann_id,
                title=body.get("title", ""),
                description=body.get("description", ""),
                announcement_date=body.get("announcement_date", "")
            )
            self.send_json({"success": True, "message": "Announcement updated successfully"})
            return

        self.send_error_json(f"Endpoint PUT {path} not found", status=404)

    # =====================================================================
    # API: DELETE HANDLER
    # =====================================================================

    def handle_api_delete(self, path: str):
        user = self.get_current_user()
        if not user or user["role"] != "admin":
            self.send_error_json("Admin privileges required", status=403)
            return

        # 1. Delete Resource
        if path.startswith("/api/resources/"):
            res_id_str = path[len("/api/resources/"):].strip()
            if res_id_str.isdigit():
                database.delete_resource(int(res_id_str))
                self.send_json({"success": True, "message": "Resource deleted successfully"})
                return

        # 2. Delete Department
        if path.startswith("/api/departments/"):
            dept_id_str = path[len("/api/departments/"):].strip()
            if dept_id_str.isdigit():
                database.delete_department(int(dept_id_str))
                self.send_json({"success": True, "message": "Department deleted successfully"})
                return

        # 3. Delete Announcement
        if path.startswith("/api/announcements/"):
            ann_id_str = path[len("/api/announcements/"):].strip()
            if ann_id_str.isdigit():
                database.delete_announcement(int(ann_id_str))
                self.send_json({"success": True, "message": "Announcement deleted successfully"})
                return

        self.send_error_json(f"Endpoint DELETE {path} not found", status=404)

    def log_message(self, format, *args):
        """Custom request logger formatting for terminal output."""
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[0]}")


def run_server(host: str = config.HOST, port: int = config.PORT):
    """Starts the threaded HTTP server."""
    # Ensure database is initialized before starting
    if not config.DATABASE_PATH.exists():
        print("[!] Database file not found. Auto-running database initialization...")
        from setup_database import init_database
        init_database()

    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, VillageAppHandler)
    print("=" * 65)
    print(f"   Village Resources & Grievance Management System Server")
    print(f"   Running on http://localhost:{port} / http://{host}:{port}")
    print(f"   Architecture: Vanilla JS -> Python Standard Library -> SQLite")
    print(f"   Press Ctrl+C to stop the server.")
    print("=" * 65)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopping...")
    finally:
        httpd.server_close()
        print("[*] Server stopped cleanly.")


if __name__ == "__main__":
    run_server()
