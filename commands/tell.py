# commands/tell.py

from output import console
from events import emit_event


class TellCommand:
    def execute(self, character, conn, args):
        if len(args) < 2:
            return "Usage: tell <player> <message>"

        target_name = args[0]
        message = " ".join(args[1:]).strip()

        if not message:
            return "Tell them what?"

        # Find target character
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, is_logged_in FROM characters WHERE name ILIKE %s",
                (target_name,),
            )
            row = cur.fetchone()

        if not row:
            return f"No player named '{target_name}'."

        target_id, is_logged_in = row  # unpack both fields

        if target_id == character.id:
            return "You talk to yourself. It echoes strangely."

        if not is_logged_in:
            return f"{target_name.capitalize()} is not in the world right now."

        formatted = f"[cyan]{character.name} tells you, '{message}'[/cyan]"

        emit_event(
            conn,
            event_type="tell",
            sender_id=character.id,
            recipient_character_id=target_id,
            message=formatted,
            color="magenta",
        )

        console.print(f"[magenta]You tell {target_name.capitalize()}, '{message}'[/magenta]")

        return None