"""Set credentials for an existing administrator in the persistent MySQL DB."""

import re

import config
import database


EMAIL_PATTERN = (
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)


def configure_existing_admin() -> None:
    """Update email and password hash for the configured admin row only."""
    if config.DATABASE_BACKEND != "mysql":
        raise RuntimeError(
            "Administrator setup requires the configured persistent MySQL database."
        )
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,29}", config.ADMIN_USERNAME):
        raise ValueError("ADMIN_USERNAME must be a valid existing account username.")
    if not re.fullmatch(EMAIL_PATTERN, config.ADMIN_EMAIL):
        raise ValueError("ADMIN_EMAIL must be a valid email address.")
    if len(config.ADMIN_PASSWORD) < 16:
        raise ValueError("ADMIN_PASSWORD must be at least 16 characters.")

    account = database.get_user_by_login(config.ADMIN_USERNAME)
    if not account or account["role"] != "admin":
        raise ValueError(
            "No existing administrator matches ADMIN_USERNAME; no account was changed."
        )

    email_owner = database.query_one(
        "SELECT id FROM users WHERE LOWER(email) = ? AND id <> ?",
        (config.ADMIN_EMAIL, account["id"]),
    )
    if email_owner:
        raise ValueError(
            "ADMIN_EMAIL is already assigned to another account; no account was changed."
        )

    updated = database.execute_commit(
        "UPDATE users SET email = ?, password_hash = ? "
        "WHERE id = ? AND role = 'admin'",
        (config.ADMIN_EMAIL, database.hash_password(config.ADMIN_PASSWORD), account["id"]),
    )
    if updated != 1:
        raise RuntimeError(
            "The administrator record was not updated; verify database permissions and try again."
        )

    print("Existing administrator credentials updated successfully.")


if __name__ == "__main__":
    configure_existing_admin()
