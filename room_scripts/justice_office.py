from justice.checks import is_head_marshal
from events import emit_event


def handle_hire(character, conn, args, session):
    if not is_head_marshal(character):
        session.send("Only the Head marshal can hire marshals.\n")
        return

    if not args:
        session.send("Hire who?\n")
        return

    target_name = args[0].capitalize()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, title, class FROM characters WHERE LOWER(name) = LOWER(%s)",
            (target_name,)
        )
        row = cur.fetchone()

    if not row:
        session.send(f"No character named '{target_name}' exists.\n")
        return

    target_id, target_name, target_title, target_class = row


    if target_title in ('marshal', 'head_marshal'):
        session.send(f"{target_name} is already a marshal.\n")
        return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE characters SET title = 'marshal' WHERE id = %s",
            (target_id,)
        )
    conn.commit()

    session.send(f"You swear {target_name} into the Justice organization as a marshal.\n")

    emit_event(
        conn,
        event_type="room",
        location_id=character.location_id,
        sender_id=character.id,
        message=f"{character.name} swears {target_name} in as a marshal of Justice.",
    )
    
# The command keyword players type
REGISTRY = {
    "hire": handle_hire,
}
