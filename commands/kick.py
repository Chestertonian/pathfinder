"""
commands/kick.py — KickCommand (staff only)

Disconnects a named player from the server.

Usage:
    kick <name>
"""

from events import emit_event


# Registry of active sessions, keyed by character_id.
# server.py registers sessions here on connect and removes them on disconnect.
_active_sessions: dict[int, object] = {}


def register_session(character_id: int, session) -> None:
    """Called by server.py when a player enters the world."""
    _active_sessions[character_id] = session


def unregister_session(character_id: int) -> None:
    """Called by server.py when a player disconnects."""
    _active_sessions.pop(character_id, None)


class KickCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."

        if not args:
            return "Kick whom?"

        target_name = " ".join(args).lower()

        # Look up target character_id by name
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name FROM characters
                WHERE LOWER(name) = %s AND is_logged_in = TRUE
                """,
                (target_name,),
            )
            row = cur.fetchone()

        if row is None:
            return f"No logged-in player named '{target_name}'."

        target_id, target_name_proper = row

        target_session = _active_sessions.get(target_id)

        if target_session is None:
            return f"{target_name_proper} is logged in but has no active session. This shouldn't happen."

        emit_event(
            conn,
            event_type="global",
            sender_id=character.id,
            message=f"{target_name_proper} has been removed from the world.",
        )

        target_session.send("You have been kicked from the server.\n")
        target_session.kick()  # force disconnect

        return f"Kicked {target_name_proper}."