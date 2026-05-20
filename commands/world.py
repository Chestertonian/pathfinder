from events import emit_event


class WorldCommand:
    def execute(self, character, conn, args):
        if not getattr(character, "is_staff", False):
            return "You are not permitted to use the world channel."

        if not args:
            return "Broadcast what?"

        message = " ".join(args)

        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel="world",
            message=message,
            color="dark_orange",
            use_border=True,
        )

        return None