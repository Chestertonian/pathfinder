from justice.checks import is_marshal
from events import emit_event


def get_justice_rooms():
    from justice.constants import JAIL_ROOM_ID, COURT_ROOM_ID, GALLOWS_ROOM_ID
    return {
        "jail":    JAIL_ROOM_ID,
        "court":   COURT_ROOM_ID,
        "gallows": GALLOWS_ROOM_ID,
    }


def handle_move(character, conn, args, session):
    if not is_marshal(character):
        session.send("You don't have the authority to move prisoners.\n")
        return

    if not args:
        session.send("Move who where? Usage: move <player> <jail|court|gallows>\n")
        return

    if len(args) < 2:
        session.send("Where do you want to move them? Usage: move <player> <jail|court|gallows>\n")
        return

    target_name = args[0].capitalize()
    destination_key = args[1].lower()

    justice_rooms = get_justice_rooms()

    if destination_key not in justice_rooms:
        session.send("Valid destinations are: jail, court, gallows.\n")
        return

    destination_id = justice_rooms[destination_key]

    if destination_id is None:
        session.send("That room has not been configured yet.\n")
        return

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, location_id, is_detained FROM characters WHERE LOWER(name) = LOWER(%s)",
            (target_name,)
        )
        row = cur.fetchone()

    if not row:
        session.send(f"No character named '{target_name}' exists.\n")
        return

    target_id, target_name, target_location_id, target_is_detained = row

    if target_location_id != character.location_id:
        session.send(f"{target_name} is not here.\n")
        return

    if not target_is_detained:
        session.send(f"{target_name} is not detained.\n")
        return

    if target_location_id == destination_id:
        session.send(f"{target_name} is already in the {destination_key}.\n")
        return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET location_id = %s WHERE id = %s",
            (destination_id, target_id)
        )
    conn.commit()

    # Event at origin room
    emit_event(
        conn,
        event_type="room",
        location_id=character.location_id,
        sender_id=character.id,
        message=f"marshal {character.name} leads {target_name} away to the {destination_key}.",
    )

    # Event at destination room
    emit_event(
        conn,
        event_type="room",
        location_id=destination_id,
        sender_id=character.id,
        message=f"marshal {character.name} brings {target_name} into the {destination_key}.",
    )

    # Personal message to the prisoner
    emit_event(
        conn,
        event_type="system",
        sender_id=target_id,
        message=f"You are moved to the {destination_key}.",
    )

    session.send(f"You move {target_name} to the {destination_key}.\n")
    
    
def handle_release(character, conn, args, session):
    if not is_marshal(character):
        session.send("You don't have the authority to release prisoners.\n")
        return

    if not args:
        session.send("Release who?\n")
        return

    target_name = args[0].capitalize()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, location_id, is_detained FROM characters WHERE LOWER(name) = LOWER(%s)",
            (target_name,)
        )
        row = cur.fetchone()

    if not row:
        session.send(f"No character named '{target_name}' exists.\n")
        return

    target_id, target_name, target_location_id, target_is_detained = row

    if target_location_id != character.location_id:
        session.send(f"{target_name} is not here.\n")
        return

    if not target_is_detained:
        session.send(f"{target_name} is not detained.\n")
        return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET is_detained = FALSE WHERE id = %s",
            (target_id,)
        )
    conn.commit()

    session.send(f"You release {target_name}.\n")

    emit_event(
        conn,
        event_type="room",
        location_id=character.location_id,
        sender_id=character.id,
        message=f"Marshall {character.name} releases {target_name}.",
    )

    emit_event(
        conn,
        event_type="system",
        sender_id=target_id,
        message="You have been released.",
    )
    
    
REGISTRY = {
    "move": handle_move,
    "release": handle_release,
}

def on_command(character, room, verb, args, conn, session):
    handler = REGISTRY.get(verb)
    if handler is None:
        return False
    handler(character, conn, args, session)
    return True