"""Vercel entry point for the GramSeva application.

This adapter lets the existing standard-library HTTP handler run as a WSGI app.
The application still uses SQLite and in-memory sessions, so this is intended for
academic demos and small evaluations rather than durable production workloads.
"""

import io
import os
import sys
import tempfile
from http.client import responses
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import config

# Vercel functions cannot write to the project directory. Keep the demo database
# in /tmp and initialize it on a fresh function instance.
config.DATABASE_PATH = Path(tempfile.gettempdir()) / "gramseva-village-system.db"

import server


class VercelVillageAppHandler(server.VillageAppHandler):
    """Use the existing routing logic without socket logging requirements."""

    def log_request(self, *args, **kwargs):
        pass

    def send_response(self, status, message=None):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass


class RequestHeaders(dict):
    """Small case-insensitive-enough header mapping for the existing handler."""

    def get(self, key, default=None):
        value = super().get(key)
        if value is not None:
            return value
        lower_key = key.lower()
        for header, header_value in self.items():
            if header.lower() == lower_key:
                return header_value
        return default


class WSGIHandler:
    """Minimal socket-like surface required by VillageAppHandler."""

    def __init__(self, environ):
        self.path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        if query:
            self.path += "?" + query
        self.command = environ.get("REQUEST_METHOD", "GET")
        self.requestline = f"{self.command} {self.path} HTTP/1.1"
        self.request_version = "HTTP/1.1"
        self.headers = RequestHeaders()
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-")
                self.headers[header_name] = value
        if environ.get("CONTENT_LENGTH"):
            self.headers["Content-Length"] = environ["CONTENT_LENGTH"]
        if environ.get("CONTENT_TYPE"):
            self.headers["Content-Type"] = environ["CONTENT_TYPE"]
        self.rfile = environ.get("wsgi.input", io.BytesIO())
        self.wfile = io.BytesIO()
        self.status = 200
        self.response_headers = []

    def send_response(self, status, message=None):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    def log_date_time_string(self):
        return "vercel"


def ensure_database():
    if not config.DATABASE_PATH.exists():
        from setup_database import init_database
        init_database()


def app(environ, start_response):
    ensure_database()
    request = WSGIHandler(environ)
    handler = object.__new__(VercelVillageAppHandler)
    handler.__dict__.update(request.__dict__)

    method = request.command.upper()
    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()
    elif method == "PUT":
        handler.do_PUT()
    elif method == "DELETE":
        handler.do_DELETE()
    elif method == "OPTIONS":
        handler.do_OPTIONS()
    else:
        handler.send_error_json("Method Not Allowed", status=405)

    body = request.wfile.getvalue()
    headers = list(request.response_headers)
    if not any(key.lower() == "content-length" for key, _ in headers):
        headers.append(("Content-Length", str(len(body))))
    reason = responses.get(request.status, "")
    start_response(f"{request.status} {reason}", headers)
    return [body]
