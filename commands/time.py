"""
commands/time.py — TimeCommand

Displays the current in-game time as a natural English phrase.
Uses the same logic as the bell thread so they're always consistent.

No emit_event() needed — personal UI panel.
"""

from datetime import datetime
from output import console, COLOR_FLAVOR


# Reuse the same word tables as the bell
_HOUR_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}


def _time_phrase(hour_24: int, minute: int) -> str:
    hour_12 = hour_24 % 12 or 12
    hour_word = _HOUR_WORDS[hour_12]

    if minute == 0:
        return f"It is {hour_word} o'clock."
    elif minute == 15:
        return f"It is quarter past {hour_word}."
    elif minute == 30:
        return f"It is half past {hour_word}."
    elif minute == 45:
        next_hour = (hour_12 % 12) + 1
        return f"It is quarter to {_HOUR_WORDS[next_hour]}."
    elif minute < 30:
        return f"It is {minute} minutes past {hour_word}."
    else:
        minutes_to = 60 - minute
        next_hour = (hour_12 % 12) + 1
        return f"It is {minutes_to} minutes to {_HOUR_WORDS[next_hour]}."


class TimeCommand:
    def execute(self, character, conn, args, session):
        now = datetime.now()
        phrase = _time_phrase(now.hour, now.minute)

        session.send(f"{phrase}")

        return None
