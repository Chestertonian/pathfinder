

class HistoryCommand:
    def execute(self, character, conn, args, session):
        channel = args[0].lower() if args else "chat"
        limit = 20

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
            return f"No history for channel {channel}."

        lines = [f"\n--- Last {limit} messages in {channel.capitalize()} ---"]
        for name, message, created_at in reversed(rows):
            timestamp = created_at.strftime("%H:%M")
            lines.append(f"  [{timestamp}] {name.capitalize()}: {message}")
        lines.append("-" * 40)

        return "\n".join(lines)