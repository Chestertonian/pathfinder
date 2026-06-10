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


def run_login(session) -> int | None:
    session.send("\n=== LOGIN ===\n")
    # removed the duplicate "Character name: " that was here
    max_attempts = 3

    with get_connection() as conn:
        with conn.cursor() as cur:

            for attempt in range(max_attempts):
                session.send("\nCharacter name: ")
                name = session.recv()

                if not name:
                    session.send("No name entered.\n")
                    continue

                character = get_character_by_name(cur, name)

                if character is None:
                    session.send(f"No character named '{name}' exists.\n")
                    session.send("(Use 'Create New Character' from the main menu.)\n")
                    continue

                if character["is_logged_in"]:
                    session.send(f"{name.capitalize()} is already in the world.\n")
                    continue

                session.send("Password: ")
                password = session.recv()

                if verify_password(password, character["password_hash"]):
                    session.send(f"\nWelcome back, {character['name'].capitalize()}.\n\n")

                    cur.execute(
                        "UPDATE characters SET is_logged_in = TRUE WHERE id = %s",
                        (character["id"],)
                    )
                    conn.commit()

                    message = f"{name.capitalize()} enters the realm."
                    border = "-----------------------------"
                    total_width = 90
                    border_pad = " " * ((total_width - len(border)) // 2)
                    message_pad = " " * ((total_width - len(message)) // 2)

                    lines = [
                        "\n",
                        border_pad + border,
                        message_pad + message,
                        border_pad + border,
                        "\n",
                    ]
                    emit_event(
                        conn,
                        event_type="global",
                        sender_id=character["id"],
                        message="\n".join(lines),
                    )

                    return character["id"]

                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    session.send(f"Incorrect password. {remaining} attempt(s) remaining.\n")
                else:
                    session.send("Incorrect password.\n")

    session.send("\nToo many failed attempts. Returning to main menu.\n\n")
    return None