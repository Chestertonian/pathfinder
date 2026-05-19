from events import emit_event

class ChatCommand:
    def execute(self, character, conn, args):
        if not args:
            return "Say what?"

        message = " ".join(args)

        emit_event(
            conn,
            event_type="chat",
            sender_id=character.id,
            message=message,
            channel="global"  
        )