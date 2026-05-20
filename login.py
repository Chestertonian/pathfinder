"""
login.py — Existing character login flow
"""

import getpass

from db import get_connection
from character_creation import verify_password
from events import emit_event 
from output import blank, print_error, print_info, print_success, prompt, rule


def get_character_by_name(cur, name: str) -> dict | None:
    cur.execute(
        "SELECT id, name, password_hash, is_logged_in FROM characters WHERE LOWER(name) = LOWER(%s)",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "password_hash": row[2], "is_logged_in": row[3]}


def run_login() -> int | None:
    """
    Run the login flow.
    Returns the character_id on success, or None if the player fails or gives up.
    """
    rule("LOGIN")
    max_attempts = 3

    # One connection for the entire login flow
    with get_connection() as conn:
        with conn.cursor() as cur:

            for attempt in range(max_attempts):
                blank()
                name = prompt("Character name:")

                if not name:
                    print_error("No name entered.")
                    continue

                character = get_character_by_name(cur, name)  # pass cursor in

                character = get_character_by_name(cur, name)

                if character is None:
                    print_error(f"No character named '{name}' exists.")
                    print_info("(Use 'Create New Character' from the main menu to make one.)")
                    continue

                if character["is_logged_in"]:
                    print_error(f"{name.capitalize()} is already in the world.")
                    continue

                password = getpass.getpass("Password: ")

                if verify_password(password, character["password_hash"]):
                    blank()
                    print_success(f"Welcome back, {character['name'].capitalize()}.")
                    blank()

                    # Mark as logged in
                    cur.execute(
                        "UPDATE characters SET is_logged_in = TRUE WHERE id = %s",
                        (character["id"],)  # FIX: was character_id
                    )
                    conn.commit()

                    # Announce arrival to the world
                    emit_event(
                        conn,
                        event_type="global",
                        sender_id=character["id"],  # FIX: was character.id
                        message=f"<< {character['name'].capitalize()} enters the world. >>",
                    )

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