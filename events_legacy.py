def emit_event(
    conn,
    *,
    event_type: str,
    sender_id: int,
    message: str,
    location_id=None,
    recipient_character_id=None,
    channel=None,
    color="white",
    use_border=False,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO broadcast_messages
                (event_type, character_id, message, color, use_border,
                 location_id, recipient_character_id, channel)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_type,
                sender_id,
                message,
                color,
                use_border,
                location_id,
                recipient_character_id,
                channel,
            ),
        )
    conn.commit()