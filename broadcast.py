"""
broadcast.py — Background broadcast message poller

Runs in a daemon thread alongside the game loop.
Every few seconds it checks broadcast_messages for new rows relevant
to this player (global messages + messages for their current room)
and prints them to the terminal.

Usage:
    poller = BroadcastPoller(starting_id, character_id)
    poller.start()
    ...
    poller.stop()
"""

import threading

from db import get_connection
from models import BroadcastMessage, Character
from commands.proclaim import _print_message

POLL_INTERVAL = 4  # seconds between checks


class BroadcastPoller:
    """
    Polls for new broadcast messages in the background.

    Needs character_id (not location_id directly) because the player
    can move between rooms — we re-fetch their current location each
    poll cycle so room-scoped announces reach them wherever they are.
    """

    def __init__(self, starting_id: int, character_id: int):
        self._last_id     = starting_id
        self._character_id = character_id
        self._stop_event  = threading.Event()
        self._thread      = threading.Thread(target=self._poll_loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=POLL_INTERVAL + 1)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_messages()
            except Exception:
                pass
            self._stop_event.wait(timeout=POLL_INTERVAL)

    def _check_messages(self) -> None:
        with get_connection() as conn:
            # Re-fetch location each cycle so room messages follow the player
            character = Character.get_by_id(conn, self._character_id)
            if character is None:
                return
            messages = BroadcastMessage.get_since(
                conn, self._last_id, character.location_id
            )

        for msg in messages:
            from output import console
            console.print()
            _print_message(msg.message, msg.color, msg.use_border)
            console.print()
            self._last_id = msg.id