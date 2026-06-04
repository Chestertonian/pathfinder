"""
commands/merchant_channel.py — Merchant guild channel

Usage:
    merchant <message>

Only accessible to Merchants.
"""

from events import emit_event


class MerchantChannelCommand:
    def execute(self, character, conn, args, session):
        if (character.char_class or "").lower() != "merchant":
            return "You don't have access to that channel."

        if not args:
            return "Say what on the merchant channel?"

        message = " ".join(args)

        emit_event(
            conn,
            event_type="channel",
            sender_id=character.id,
            channel="merchant",
            message=message,
        )