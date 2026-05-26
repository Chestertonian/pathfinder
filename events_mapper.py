from event_types import Event

def row_to_event(row) -> Event:
    return Event(
        id=row[0],
        event_type=row[1],

        sender_id=row[2],
        recipient_character_id=row[3],

        location_id=row[4],
        channel=row[5],
        message=row[6],
        color=row[7],
        use_border=row[8],
        created_at=row[9],     # ADDED
    )