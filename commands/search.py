"""
commands/search.py — SCommand

Emits two events:
    - room  : "Name searches around a bit." (visible to others in the room)
    - system: the actual search result (visible only to the user)
"""

from events import emit_event
from output import print_info, console


class SearchCommand:
    def execute(self, character, conn, args, session):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT search FROM locations WHERE id = %s",
                (character.location_id,),
            )
            row = cur.fetchone()

        if row is None:
            return "You don't seem to be anywhere."

        search = row[0]

        # Tell the room what the character is doing
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} searches around a bit.",
            use_border=False,
        )

        # Tell the user what they find
        if not search or not search.strip():
            session.send("You don't find anything notable.\n")
        else:
            session.send(f"{search}\n")

        return None
