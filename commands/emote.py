from events import emit_event
from output import console


class EmoteCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Emote what?"

        action = " ".join(args).strip()

        # prevent empty junk
        if not action:
            return "Emote what?"

        room = character.get_room(conn)

        # ensure punctuation
        if not action.endswith((".", "!", "?")):
            action += "."

        message = f"{character.name} {action}"

        emit_event(
            conn,
            event_type="room",
            sender_id=character.id,
            location_id=character.location_id,
            message=message,
        )
        
        session.send(message+"\n")

        return None