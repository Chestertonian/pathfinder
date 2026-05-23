from events import emit_event

class ChatCommand:
    def execute(self, character, conn, args, session):
        if not args:
            return "Say what?"

        message = " ".join(args)

        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel="chat",
            message=message,
            color="cyan",
        )