from app.handlers.order_flow import handle_order_flow_message
from app.services.webhook_dedupe import is_duplicate_message


def handle_webhook_payload(data: dict) -> None:
    entries = data.get("entry") or []
    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            value = change.get("value") or {}

            if value.get("statuses"):
                print("Ignoring status event.")
                continue

            incoming_messages = value.get("messages") or []
            if not incoming_messages:
                print("No incoming user messages found in payload.")
                continue

            contacts = value.get("contacts") or []
            sender = None
            if contacts:
                sender = contacts[0].get("wa_id")

            for message in incoming_messages:
                sender_phone = sender or message.get("from")
                if not sender_phone:
                    print("Unable to determine sender phone number.")
                    continue

                message_id = message.get("id", "")
                if is_duplicate_message(message_id):
                    print(f"Ignoring duplicate webhook message event: {message_id}")
                    continue

                print(f"Incoming message from: {sender_phone}")
                handle_order_flow_message(sender_phone, message)