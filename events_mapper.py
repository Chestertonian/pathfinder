from event_types import Event

def row_to_event(row) -> Event:
    return Event(
        id=row[0],
        event_type=row[1],

        sender_id=row[2],      # character_id in DB
        recipient_character_id=row[3],   # recipient_character_id

        location_id=row[4],
        channel=row[5],
        message=row[6],
        color=row[7],
        use_border=row[8],
    )