from datetime import datetime, timezone
from events import emit_event

class RingCommand:
    def execute(self, character, conn, args, session):
        # Only "ring bell" is supported
        if not args or args[0].lower() != "bell":
            session.send("Ring what? Try: ring bell\n")
            return

        with conn.cursor() as cur:

            # 1. Does this room have a bell?
            cur.execute("""
                SELECT id, display_text FROM room_fixtures
                WHERE location_id = %s AND fixture_type = 'bell'
            """, (character.location_id,))
            fixture = cur.fetchone()

            if not fixture:
                session.send("There is no bell here.\n")
                return

            # 2. Is the bell on cooldown?
            cur.execute("""
                SELECT expires_at FROM room_cooldowns
                WHERE location_id = %s AND cooldown_type = 'bell'
            """, (character.location_id,))
            cooldown_row = cur.fetchone()

            if cooldown_row:
                expires_at = cooldown_row[0]
                now = datetime.now(timezone.utc)
                if expires_at > now:
                    session.send("The bell is still settling.\n")
                    return

            # 3. Emit room event — everyone present sees it
            emit_event(
                conn=conn,
                event_type="room",
                message=f"{character.name} rings the bell.",
                location_id=character.location_id,
                sender_id=character.id,
                color="white",
            )

            # 4. Emit guild event — all online merchants see it
            with conn.cursor() as loc_cur:
                loc_cur.execute(
                    "SELECT name FROM locations WHERE id = %s",
                    (character.location_id,)
                )
                loc_row = loc_cur.fetchone()
                room_name = loc_row[0] if loc_row else "Unknown"

            emit_event(
                conn=conn,
                event_type="guild",
                message=f"{character.name} rings the bell in {room_name}.",
                location_id=character.location_id,
                sender_id=character.id,
                color="cyan",
                guild="merchant",
            )

            # 5. Set/refresh the cooldown (upsert)
            cur.execute("""
                INSERT INTO room_cooldowns (location_id, cooldown_type, expires_at)
                VALUES (%s, 'bell', NOW() + INTERVAL '30 seconds')
                ON CONFLICT (location_id, cooldown_type)
                DO UPDATE SET expires_at = NOW() + INTERVAL '30 seconds'
            """, (character.location_id,))

            conn.commit()

        session.send("You ring the bell.\n")