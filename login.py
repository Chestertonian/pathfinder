"""
login.py — Existing character login flow

Asks for name and password, verifies against the DB,
and returns the character_id on success or None on failure.
"""

import getpass

from db import get_connection
from character_creation import verify_password
from output import blank, print_error, print_info, print_success, prompt, rule


def get_character_by_name(name: str) -> dict | None:
    """
    Look up a character by name.
    Returns a dict with id, name, and password_hash — or None if not found.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, password_hash FROM characters WHERE LOWER(name) = LOWER(%s)",
                (name,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return {"id": row[0], "name": row[1], "password_hash": row[2]}


def run_login() -> int | None:
    """
    Run the login flow.
    Returns the character_id on success, or None if the player fails or gives up.
    """
    rule("LOGIN")

    # Give the player a few attempts before kicking them back to the menu.
    # This avoids locking someone out from a single typo.
    max_attempts = 3

    for attempt in range(max_attempts):
        blank()
        name = prompt("Character name:")

        if not name:
            print_error("No name entered.")
            continue

        character = get_character_by_name(name)

        if character is None:
            print_error(f"No character named '{name}' exists.")
            print_info("(Use 'Create New Character' from the main menu to make one.)")
            continue

        password = getpass.getpass("  Password: ")

        if verify_password(password, character["password_hash"]):
            blank()
            print_success(f"Welcome back, {character['name']}.")
            blank()
            return character["id"]

        remaining = max_attempts - attempt - 1
        if remaining > 0:
            print_error(f"Incorrect password. {remaining} attempt(s) remaining.")
        else:
            print_error("Incorrect password.")

    blank()
    print_error("Too many failed attempts. Returning to main menu.")
    blank()
    return None