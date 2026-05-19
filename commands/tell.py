from models import BroadcastMessage
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

        # find target character
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM characters WHERE name ILIKE %s",
                (target_name,),
            )
            row = cur.fetchone()

        if not row:
            return f"No player named '{target_name}'."

        target_id = row[0]

        if target_id == character.id:
            return "You talk to yourself. It echoes strangely."

        formatted = f"[cyan]{character.name} tells you, '{message}'[/cyan]"

        # send ONLY to target (global message filtered by recipient_id idea)
        emit_event(
            conn,
            event_type="tell",
            sender_id=character.id,
            recipient_id=target_id,
            message=formatted
        )

        console.print(f"[cyan]You tell {target_name.capitalize()}, '{message}'[/cyan]")

        return None