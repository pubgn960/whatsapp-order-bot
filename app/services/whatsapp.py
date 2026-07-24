import requests

from config import ACCESS_TOKEN, PHONE_NUMBER_ID


def _send_whatsapp_payload(payload: dict) -> bool:
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp API credentials are not configured.")
        return False

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"WhatsApp API status: {response.status_code}")

        if not response.ok:
            print("WhatsApp API response:")
            print(response.text)

        return response.ok
    except requests.RequestException as exc:
        print(f"WhatsApp API request failed: {exc}")
        return False


def send_text_message(to: str, message: str) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    return _send_whatsapp_payload(payload)


def send_image_message(to: str, image_id: str, caption: str = "") -> bool:
    image_payload = {"id": image_id}
    if caption:
        image_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": image_payload,
    }
    return _send_whatsapp_payload(payload)


def send_document_message(to: str, document_id: str, caption: str = "") -> bool:
    document_payload = {"id": document_id}
    if caption:
        document_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": document_payload,
    }
    return _send_whatsapp_payload(payload)


def send_interactive_button_message(
    to: str,
    body_text: str,
    button_id: str,
    button_title: str,
) -> bool:
    return send_interactive_buttons_message(
        to=to,
        body_text=body_text,
        buttons=[(button_id, button_title)],
    )


def send_interactive_buttons_message(
    to: str,
    body_text: str,
    buttons: list,
) -> bool:
    formatted_buttons = []
    for button_id, button_title in buttons:
        formatted_buttons.append(
            {
                "type": "reply",
                "reply": {"id": button_id, "title": button_title},
            }
        )

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": formatted_buttons},
        },
    }
    return _send_whatsapp_payload(payload)


def send_interactive_list_message(
    to: str,
    body_text: str,
    button_text: str,
    section_title: str,
    rows: list,
) -> bool:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": section_title,
                        "rows": rows,
                    }
                ],
            },
        },
    }
    return _send_whatsapp_payload(payload)