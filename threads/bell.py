"""
threads/bell.py — Temple Bell Thread

Emits a global bell chime every 15 minutes, synchronized to real wall time.

Chime logic (standard clock):
    :00  → rings N times (1-12) + "...N o'clock"
    :15  → rings once
    :30  → rings twice
    :45  → rings three times

Runs as a daemon thread — dies automatically when the main process exits.
Call start_bell_thread() ONCE from server.py at startup — not per player.
"""

import threading
import time
from datetime import datetime


_RING_WORDS = {
    1:  "once",
    2:  "twice",
    3:  "three times",
    4:  "four times",
    5:  "five times",
    6:  "six times",
    7:  "seven times",
    8:  "eight times",
    9:  "nine times",
    10: "ten times",
    11: "eleven times",
    12: "twelve times",
}

_HOUR_WORDS = {
    1:  "one",
    2:  "two",
    3:  "three",
    4:  "four",
    5:  "five",
    6:  "six",
    7:  "seven",
    8:  "eight",
    9:  "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


def _build_message(hour_24: int, minute: int) -> str:
    hour_12 = hour_24 % 12 or 12

    if minute == 0:
        rings = _RING_WORDS[hour_12]
        hour_word = _HOUR_WORDS[hour_12]
        return f"The temple bell rings {rings} — {hour_word} o'clock."
    elif minute == 15:
        return "The temple bell rings once."
    elif minute == 30:
        return "The temple bell rings twice."
    elif minute == 45:
        return "The temple bell rings three times."
    else:
        return "The temple bell rings."


def _seconds_until_next_quarter() -> float:
    now = datetime.now()
    minutes_past_quarter = now.minute % 15
    minutes_to_wait = 15 - minutes_past_quarter
    seconds_to_wait = (minutes_to_wait * 60) - now.second
    return float(seconds_to_wait)


def _bell_loop(emit_event, conn_factory):
    last_chime = None

    while True:
        sleep_for = _seconds_until_next_quarter()
        time.sleep(sleep_for)

        now = datetime.now()

        # Unique key for this quarter-hour slot
        chime_key = (now.hour, (now.minute // 15) * 15)

        if chime_key == last_chime:
            # Already chimed this slot — boundary timing edge case
            time.sleep(5)
            continue

        last_chime = chime_key

        message = _build_message(now.hour, now.minute)

        try:
            with conn_factory() as conn:
                emit_event(
                    conn,
                    event_type="global",
                    sender_id=None,
                    message=message,
                    color="dark_orange",
                    use_border=False,
                )
        except Exception:
            import traceback
            traceback.print_exc()


def start_bell_thread(emit_event, conn_factory):
    """
    Spawn the bell as a background daemon thread.

    Call this ONCE from server.py at startup — not inside the game loop.

    Example:
        from threads.bell import start_bell_thread
        from events import emit_event
        from db import get_connection

        start_bell_thread(emit_event, get_connection)
    """
    t = threading.Thread(
        target=_bell_loop,
        args=(emit_event, conn_factory),
        daemon=True,
        name="bell-thread",
    )
    t.start()
    return t