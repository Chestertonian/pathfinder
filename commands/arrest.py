from justice.constants import JAIL_ROOM_ID
from justice.checks import is_marshal, is_detained
from events import emit_event

class ArrestCommand:
    def execute(self, character, conn, args, session):
        if not is_marshal(character):
            session.send("You don't have the authority to make arrests.\n")
            return

        if not args:
            session.send("Arrest who?\n")
            return

        if JAIL_ROOM_ID is None:
            session.send("The jail has not been configured yet.\n")
            return

        target_name = args[0].capitalize()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.location_id, c.is_detained
                FROM characters c
                WHERE LOWER(c.name) = LOWER(%s)
                """,
                (target_name,)
            )
            row = cur.fetchone()

        if not row:
            session.send(f"No character named '{target_name}' exists.\n")
            return

        target_id, target_name, target_location_id, target_is_detained = row

        # Target must be in the same room
        if target_location_id != character.location_id:
            session.send(f"{target_name} is not here.\n")
            return

        # Already detained
        if target_is_detained:
            session.send(f"{target_name} is already detained.\n")
            return

        # Detain and move to jail
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE characters SET is_detained = TRUE, location_id = %s WHERE id = %s",
                (JAIL_ROOM_ID, target_id)
            )
        conn.commit()

        # Event at the arrest location
        emit_event(
            conn,
            event_type="room",
            location_id=character.location_id,
            sender_id=character.id,
            message=f"{character.name} places {target_name} under arrest.",
        )

        # Event at the jail
        emit_event(
            conn,
            event_type="room",
            location_id=JAIL_ROOM_ID,
            sender_id=character.id,
            message=f"Marshal {character.name} brings {target_name} into custody.",
        )

        # Personal message to the arrested player
        emit_event(
            conn,
            event_type="system",
            sender_id=target_id,
            message="You have been arrested and taken to the jail.",
        )

        session.send(f"You clap {target_name} in irons and send them to the jail.\n")