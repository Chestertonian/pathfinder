"""
broadcast.py — Background event poller

Polls broadcast_messages for new events relevant to this player,
renders them, and prints them.

The poller itself should stay dumb:

    fetch events
    check delivery
    render
    print
"""

import threading
import traceback

from db import get_connection
from models import Character

from events import should_deliver, get_visible_events
from render import render_event

POLL_INTERVAL = 0.2


class BroadcastPoller:

    def __init__(self, starting_id: int, character_id: int, session):  # CHANGED: added session
        self._last_id = starting_id
        self._character_id = character_id
        self._session = session                                         # CHANGED: store it

        self._stop_event = threading.Event()

        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
        )

    # ------------------------------------------------------------------
    # Lifecycle — UNCHANGED
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=POLL_INTERVAL + 1)

    # ------------------------------------------------------------------
    # Main loop — UNCHANGED
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_messages()
            except Exception:
                traceback.print_exc()
            self._stop_event.wait(timeout=POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Poll cycle
    # ------------------------------------------------------------------

    def _check_messages(self) -> None:

        with get_connection() as conn:

            character = Character.get_by_id(conn, self._character_id)

            if character is None:
                return

            messages = get_visible_events(conn, last_id=self._last_id, character=character)

            for msg in messages:
                self._last_id = max(self._last_id, msg.id)

                if not should_deliver(character, msg):
                    continue

                text = render_event(conn, msg)

                self._session.send(text + "\n")  # CHANGED: was console.print(text)