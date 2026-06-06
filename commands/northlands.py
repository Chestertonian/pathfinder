from events import emit_event

class NorthlandsCommand:
    def execute(self, character, conn, args, sessgion):
        if not args:
            return "Say what?"

        message = " ".join(args)

        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel="northlands",
            message=message,
            color="blue",
        )