"""
powers/handlers/salute.py — Fighter's Salute

Usage:
    salute            → untargeted, self-display only
    salute <fighter>  → targeted, must be a fighter in the room

Fighters only. Target must also be a fighter.
"""

from events import emit_event
from output import to_ansi


def execute(character, target, args, conn, session) -> None:

    name = character.name.capitalize()

    # --- Untargeted ---
    if target is None:
        msg = to_ansi(
            f"[bright_green]{name} raises a clenched fist to their chest "
            f"and bows their head in a fighter's salute.[/bright_green]"
        )
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=msg,
        )
        session.send(
            to_ansi(
                f"[bright_green]You raise a clenched fist to your chest "
                f"and bow your head in a fighter's salute.[/bright_green]\n"
            )
        )
        return

    # --- Targeted --- target must be a fighter
    if target["type"] != "player":
        session.send("You can only salute fellow fighters.\n")
        return

    # Check target is a fighter
    with conn.cursor() as cur:
        cur.execute(
            "SELECT class FROM characters WHERE id = %s",
            (target["id"],)
        )
        row = cur.fetchone()

    if row is None or (row[0] or "").lower() != "fighter":
        session.send(
            f"{target['name'].capitalize()} is not a fighter. "
            f"The salute is for warriors only.\n"
        )
        return

    target_name = target["name"].capitalize()

    # Room sees it
    msg = to_ansi(
        f"[bright_green]{name} acknowledges {target_name} "
        f"with a brief, respectful fighter's salute.[/bright_green]"
    )
    emit_event(
        conn,
        event_type="room",
        sender_id=character.id,
        location_id=character.location_id,
        message=msg,
    )

    # Sender sees their own action
    session.send(
        to_ansi(
            f"[bright_green]You acknowledge {target_name} "
            f"with a brief, respectful fighter's salute.[/bright_green]\n"
        )
    )