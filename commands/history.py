from commands.channels import CHANNELS


class HistoryCommand:
    def execute(self, character, conn, args, session):
        channel = args[0].lower() if args else "chat"
        limit = 20

        # Check access using the same registry as sending/receiving
        entry = CHANNELS.get(channel)
        if entry is None:
            return f"No channel '{channel}' exists."

        display_name, access_check, color = entry
        if not access_check(character):
            return f"You don't have access to the {display_name} channel."

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, bm.message, bm.created_at
                FROM broadcast_messages bm
                JOIN characters c ON c.id = bm.character_id
                WHERE bm.event_type = 'channel'
                  AND bm.channel = %s
                ORDER BY bm.id DESC
                LIMIT %s
                """,
                (channel, limit),
            )
            rows = cur.fetchall()

        if not rows:
            return f"No history for {display_name}."

        lines = [f"\n--- Last {limit} messages in {display_name} ---"]
        for name, message, created_at in reversed(rows):
            timestamp = created_at.strftime("%m/%d %H:%M")
            lines.append(f"  [{timestamp}] {name.capitalize()}: {message}")
        lines.append("-" * 40)

        return "\n".join(lines)