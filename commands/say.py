# commands/say.py

from models import BroadcastMessage
from output import blank, console, print_error, print_flavor, print_success, prompt


class SayCommand:
    def execute(self, character, conn, args):
        if not args:
            return "Say what?"

        text = " ".join(args)
        text=text.capitalize()
        if not text.endswith(("!", "?", ".")):
            text += "."

        room = character.get_room(conn)

        BroadcastMessage.announce(
            conn,
            room.id,
            f"{character.name} says, '{text}'",
            sender_character_id=character.id
        )
        console.print(f"You say{text}.")

        return None