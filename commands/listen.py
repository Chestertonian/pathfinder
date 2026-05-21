"""
commands/listen.py — ListenCommand

Emits two events:
    - room  : "*Name pauses to listen." (visible to others in the room)
    - system: the actual sound description (visible only to the user)

If the location has no sound set, tells the user there's nothing notable.
"""

from events import emit_event
from output import print_info, console


class ListenCommand:
    def execute(self, character, conn, args):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sound FROM locations WHERE id = %s",
                (character.location_id,),
            )
            row = cur.fetchone()

        if row is None:
            return "You don't seem to be anywhere."

        sound = row[0]

        # Tell the room what the character is doing
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} pauses to listen.",
            color="grey54",
            use_border=False,
        )

        # Tell the user what they hear
        if not sound or not sound.strip():
            print_info("You don't hear anything notable.")
        else:
            console.print(f"[blue]{sound}[/]")

        return None
