# commands/say.py

import re

from models import BroadcastMessage
from events import emit_event
from output import blank, console, print_error, print_flavor, print_success, prompt


class SayCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Say what?"



        text = " ".join(args).strip()

        # Capitalize start of string and start of sentences.
        text = re.sub(
            r'(^|[.!?]\s+)([a-z])',
            lambda m: m.group(1) + m.group(2).upper(),
            text
        )

        if not text.endswith(("!", "?", ".")):
            text += "."

        room = character.get_room(conn)

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=f'{character.name} says, "{text}"',
        )
        session.send(f"You say, \"{text}\"\n")

        return None