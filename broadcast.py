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
import traceback

from db import get_connection
from models import BroadcastMessage, Character
from commands.proclaim import _print_message
from delivery import should_deliver
from render import render

POLL_INTERVAL = 0.2  # seconds between checks


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
            except Exception as e:
                traceback.print_exc()
            self._stop_event.wait(timeout=POLL_INTERVAL)

    def _check_messages(self) -> None:
        with get_connection() as conn:
            character = Character.get_by_id(conn, self._character_id)
            if character is None:
                return

            messages = BroadcastMessage.get_since(
                conn,
                self._last_id,
                character.location_id,
                self._character_id
            )

        from output import console

        for msg in messages:
            
            self._last_id = max(self._last_id, msg.id)

            # 1. delivery gate
            if not should_deliver(msg, character):
                continue

            with get_connection() as conn:
                lookup = lambda cid: Character.get_by_id(conn, cid)

                text = render(msg, lookup)

            # 3. output
            console.print(text)