from models import BroadcastMessage
from output import console


class EmoteCommand:
    def execute(self, character, conn, args):
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

        BroadcastMessage.announce(
            conn,
            room.id,
            message,
            sender_character_id=character.id
        )

        console.print(f"{character.name} {action}")

        return None