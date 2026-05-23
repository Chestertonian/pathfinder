"""
commands/shutdown.py — ShutdownCommand (staff only)

Gracefully stops the server from inside the game.
"""

import os
import signal
import threading

from events import emit_event


class ShutdownCommand:
    def execute(self, character, conn, args, session):
        if not character.is_staff:
            return "You don't have permission to do that."

        delay = 0
        if args and args[0].isdigit():
            delay = int(args[0])

        message = (
            f"Server is shutting down in {delay} seconds."
            if delay
            else "Server is shutting down now."
        )

        emit_event(
            conn,
            event_type="global",
            sender_id=character.id,
            message=message,
        )

        def _do_shutdown():
            # Mark all characters offline before pulling the plug
            from db import get_connection
            with get_connection() as c:
                with c.cursor() as cur:
                    cur.execute("UPDATE characters SET is_logged_in = FALSE")
                c.commit()

            os.kill(os.getpid(), signal.SIGINT)

        if delay:
            threading.Timer(delay, _do_shutdown).start()
        else:
            _do_shutdown()

        return None