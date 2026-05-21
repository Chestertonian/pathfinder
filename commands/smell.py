"""
commands/smell.py — SmellCommand

Emits two events:
    - room  : "*Name sniffs the air." (visible to others in the room)
    - system: the actual smell description (visible only to the user)

If the location has no smell set, tells the user there's nothing notable.
"""

from events import emit_event
from output import print_info, console


class SmellCommand:
    def execute(self, character, conn, args):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT smell FROM locations WHERE id = %s",
                (character.location_id,),
            )
            row = cur.fetchone()

        if row is None:
            return "You don't seem to be anywhere."

        smell = row[0]

        # Tell the room what the character is doing
        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f"{character.name} sniffs the air.",
            color="grey54",
            use_border=False,
        )

        # Tell the user what they smell
        if not smell or not smell.strip():
            print_info("You don't smell anything notable.")
        else:
            console.print(f"[red]{smell}[/]")

        return None
