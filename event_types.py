from dataclasses import dataclass
from typing import Optional


@dataclass
class Event:
    id: int
    event_type: str

    sender_id: Optional[int]
    recipient_character_id: Optional[int]

    location_id: Optional[int]
    channel: Optional[str]

    message: str
    color: str
    use_border: bool