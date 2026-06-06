"""
powers/handlers/pray.py — Pray

Only usable in the Plane of the Dead (room 246).
Returns the character to the world.
Available to all characters regardless of class.
"""

from events import emit_event

PLANE_OF_DEAD_ID = 246
RESPAWN_ROOM_ID  = 1


def execute(character, target, args, conn, session) -> None:

    if character.location_id != PLANE_OF_DEAD_ID:
        session.send("There is nothing to pray to here.\n")
        return

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE characters
            SET location_id     = %s,
                room_entered_at = NOW(),
                pending_look    = TRUE
            WHERE id = %s
            """,
            (RESPAWN_ROOM_ID, character.id),
        )
    conn.commit()

    session.send("\n".join([
        "",
        "  A warmth returns to your limbs.",
        "",
        "  The grey recedes.",
        "",
        "  You wake, gasping, on cold stone.",
        "",
    ]))