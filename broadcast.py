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
from models import BroadcastMessage, Character

from delivery import should_deliver
print("Delivery module loaded.")
from render import render_event

POLL_INTERVAL = 0.2


class BroadcastPoller:

    def __init__(self, starting_id: int, character_id: int):

        self._last_id = starting_id
        self._character_id = character_id

        self._stop_event = threading.Event()

        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=POLL_INTERVAL + 1)

    # ------------------------------------------------------------------
    # Main loop
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

            # Refresh character every cycle
            character = Character.get_by_id(
                conn,
                self._character_id
            )

            if character is None:
                return

            # Fetch ALL newer messages
            messages = BroadcastMessage.get_since(
                conn,
                self._last_id
            )

            # Process in-order
            for msg in messages:

                # Advance cursor immediately
                self._last_id = max(self._last_id, msg.id)
                
                # Delivery gate
                if not should_deliver(msg, character):
                    continue

                # Render
                text = render_event(conn, msg)

                # Output
                from output import console
                console.print(text)