"""
login.py — Existing character login flow
"""

from db import get_connection
from character_creation import verify_password
from events import emit_event
from output import blank, print_error, print_info, print_success, rule


def get_character_by_name(cur, name: str) -> dict | None:
    cur.execute(
        "SELECT id, name, password_hash, is_logged_in FROM characters WHERE LOWER(name) = LOWER(%s)",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "password_hash": row[2], "is_logged_in": row[3]}


def run_login(session) -> int | None:        # CHANGED: accepts session
    """
    Run the login flow.
    Returns the character_id on success, or None if the player fails or gives up.
    """
    session.send("\n=== LOGIN ===\n")
    session.send("Character name: ")
    max_attempts = 3

    with get_connection() as conn:
        with conn.cursor() as cur:

            for attempt in range(max_attempts):
                session.send("\n")           # CHANGED: was blank()

                session.send("Character name: ")          # CHANGED: was prompt()
                name = session.recv()                     # CHANGED: reads from socket

                if not name:
                    session.send("No name entered.\n")    # CHANGED: was print_error()
                    continue

                character = get_character_by_name(cur, name)

                if character is None:
                    session.send(f"No character named '{name}' exists.\n")
                    session.send("(Use 'Create New Character' from the main menu.)\n")
                    continue

                if character["is_logged_in"]:
                    session.send(f"{name.capitalize()} is already in the world.\n")
                    continue

                session.send("Password: ")               # CHANGED: was getpass.getpass()
                password = session.recv()                # CHANGED: plain text for now

                if verify_password(password, character["password_hash"]):
                    session.send("\n")
                    session.send(f"Welcome back, {character['name'].capitalize()}.\n")
                    session.send("\n")

                    cur.execute(
                        "UPDATE characters SET is_logged_in = TRUE WHERE id = %s",
                        (character["id"],)
                    )
                    conn.commit()

                    emit_event(
                        conn,
                        event_type="global",
                        sender_id=character["id"],
                        message=f"<< {character['name'].capitalize()} enters the world. >>",
                        # CHANGED: stripped Rich tags from message — plain text now
                    )

                    return character["id"]

                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    session.send(f"Incorrect password. {remaining} attempt(s) remaining.\n")
                else:
                    session.send("Incorrect password.\n")

    session.send("\nToo many failed attempts. Returning to main menu.\n\n")
    return None