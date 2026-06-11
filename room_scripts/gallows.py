from justice.checks import is_head_marshal, is_detained
from justice.constants import GALLOWS_ROOM_ID
from events import emit_event
from combat.death import resolve_death  # adjust to your actual import


def handle_execute(character, conn, args, session):
    if not is_head_marshal(character):
        session.send("Only the Head marshal can carry out an execution.\n")
        return

    if not args:
        session.send("Execute who?\n")
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

    if target_location_id != GALLOWS_ROOM_ID:
        session.send(f"{target_name} is not at the gallows.\n")
        return

    if not target_is_detained:
        session.send(f"{target_name} has not been detained.\n")
        return

    # Kill the prisoner, crediting "Gallows" as the killer
    resolve_death(
        conn=conn,
        dead_id=target_id,
        dead_type = 'character',
        killer_type="npc",
        killer_id=49,
        location_id=GALLOWS_ROOM_ID,
    )

    # Clear detained status after death resolves
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET is_detained = FALSE WHERE id = %s",
            (target_id,)
        )
    conn.commit()

    session.send(f"The sentence has been carried out. {target_name} has been hanged.\n")
    

REGISTRY = {
    "execute": handle_execute,
}

def on_command(character, room, verb, args, conn, session):
    handler = REGISTRY.get(verb)
    if handler is None:
        return False
    handler(character, conn, args, session)
    return True