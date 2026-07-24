from app.services.conversation_state import get_state, update_state
from app.services.whatsapp import (
    send_document_message,
    send_image_message,
    send_interactive_button_message,
    send_interactive_buttons_message,
    send_interactive_list_message,
    send_text_message,
)
from config import ADMIN_PHONE
from database import get_categories, get_packages, get_price

WELCOME_TEXT = (
    "👋 Assalam-o-Alaikum!\n\n"
    "Welcome to Alyan Gamer\n\n"
    "━━━━━━━━━━━━━━\n\n"
    "🎮 COD Mobile Top Up\n\n"
    "Fast • Secure • Trusted\n\n"
    "Please press Continue."
)

GAME_SELECTION_TEXT = "🎮 Select Game"
CATEGORY_SELECTION_TEXT = "📂 Select Category"

PACKAGE_HEADER = "💎 Select CP Package"

LOGIN_METHOD_TEXT = "🔐 Select Login Method"
PAYMENT_METHOD_TEXT = "💳 Select Payment Method"

ACCOUNT_DETAILS_ONE_MESSAGE_HINT = "Please send all details in ONE message."
PAYMENT_SCREENSHOT_REQUIRED_TEXT = "Please upload your payment screenshot."

PAYMENT_METHOD_OPTIONS = [
    ("payment_binance", "Binance"),
    ("payment_bybit", "Bybit"),
    ("payment_tron_trc20", "Tron (TRC20)"),
    ("payment_no_method", "Need Payment Help"),
]

BINANCE_PAYMENT_TEXT = (
    "💰 Binance Payment\n\n"
    "Account:\n"
    "Alyan-Gamer-Support\n\n"
    "Binance ID:\n"
    "738316002\n\n"
    "Please send the required USDT payment.\n\n"
    "After payment, upload your payment screenshot in this chat."
)

BYBIT_PAYMENT_TEXT = (
    "💰 Bybit Payment\n\n"
    "Account:\n"
    "AlyanGamer\n\n"
    "UID:\n"
    "481517334\n\n"
    "Please send the required USDT payment.\n\n"
    "After payment, upload your payment screenshot in this chat."
)

TRON_PAYMENT_TEXT = (
    "💰 USDT (TRC20)\n\n"
    "Wallet Address:\n\n"
    "TUsTM5QqahDCFUZy5ygcRPTY7YKPhYDM4K\n\n"
    "Please send the required USDT payment.\n\n"
    "After payment, upload your payment screenshot in this chat."
)

NO_PAYMENT_METHOD_TEXT = (
    "No problem 😊\n\n"
    "Our support team has been notified.\n\n"
    "Please wait while we help you choose another payment method."
)

PAYMENT_SCREENSHOT_RECEIVED_TEXT = (
    "✅ Payment screenshot received successfully.\n\n"
    "Your order has been submitted.\n\n"
    "Please wait while our team verifies your payment."
)

STEP_GUARD_TEXT = "Please complete the current step first."

CATEGORY_EMOJI_MAP = {
    "normal orders": "📦",
    "special packs": "🎉",
}

_ORDER_COUNTER = 0
_ORDER_CUSTOMER_INDEX = {}
_ACTIVE_ORDER_STATUSES = {"pending_verification", "accepted", "processing"}
_ADMIN_ACTION_BUTTONS = [
    ("admin_accept", "✅ Accept"),
    ("admin_processing", "🔄 Processing"),
    ("admin_completed", "🎉 Completed"),
    ("admin_reject", "❌ Reject"),
]
_ADMIN_ACTION_TO_STATUS = {
    "admin_accept": "accepted",
    "admin_processing": "processing",
    "admin_completed": "completed",
    "admin_reject": "rejected",
}


def _build_activision_template(selected_package: str) -> str:
    package_line = selected_package or "Not selected"
    return (
        "✅ Login Method: Activision\n\n"
        f"CP Package: {package_line}\n\n"
        "Copy and fill this template, then send in ONE message:\n\n"
        "Email:\n"
        "Password:\n"
        "Ingame Name:"
    )


def _build_facebook_template(selected_package: str) -> str:
    package_line = selected_package or "Not selected"
    return (
        "✅ Login Method: Facebook\n\n"
        f"CP Package: {package_line}\n\n"
        "Copy and fill this template, then send in ONE message:\n\n"
        "Email:\n"
        "Password:\n"
        "Ingame Name:\n"
        "Recovery Codes:"
    )


def _field_alias_to_key(field_alias: str) -> str:
    normalized = "".join(ch for ch in field_alias.lower() if ch.isalnum())
    alias_map = {
        "email": "email",
        "password": "password",
        "ingamename": "ingame_name",
        "ingame": "ingame_name",
        "recovercodes": "recovery_codes",
        "recoverycode": "recovery_codes",
        "recoverycodes": "recovery_codes",
    }
    return alias_map.get(normalized, "")


def _parse_account_details(text_body: str) -> dict:
    parsed = {}
    lines = text_body.splitlines()
    for line in lines:
        if ":" not in line:
            continue
        field_name, field_value = line.split(":", 1)
        key = _field_alias_to_key(field_name.strip())
        if not key:
            continue
        value = field_value.strip()
        if value:
            parsed[key] = value
    return parsed


def _required_fields_for_login_method(login_method: str) -> list:
    required = [
        ("Email", "email"),
        ("Password", "password"),
        ("Ingame Name", "ingame_name"),
    ]
    if login_method == "Facebook":
        required.append(("Recovery Codes", "recovery_codes"))
    return required


def _get_missing_fields(login_method: str, parsed_details: dict) -> list:
    missing_labels = []
    for label, key in _required_fields_for_login_method(login_method):
        if not (parsed_details.get(key) or "").strip():
            missing_labels.append(label)
    return missing_labels


def _send_welcome_continue(user_phone: str) -> bool:
    return send_interactive_button_message(
        to=user_phone,
        body_text=WELCOME_TEXT,
        button_id="continue_flow",
        button_title="Continue",
    )


def _send_game_button(user_phone: str) -> bool:
    return send_interactive_button_message(
        to=user_phone,
        body_text=GAME_SELECTION_TEXT,
        button_id="game_cod_mobile",
        button_title="COD Mobile",
    )


def _category_button_id(category: str) -> str:
    normalized = category.lower().replace(" ", "_")
    return f"category_{normalized}"


def _send_category_buttons(user_phone: str) -> bool:
    categories = get_categories()
    if not categories:
        print("No active categories found in database.")
        return send_text_message(
            user_phone,
            "No categories are available right now. Please try again later.",
        )

    buttons = []
    for category in categories[:3]:
        emoji = CATEGORY_EMOJI_MAP.get(category.lower(), "📦")
        buttons.append((_category_button_id(category), f"{emoji} {category}"))

    return send_interactive_buttons_message(
        to=user_phone,
        body_text=CATEGORY_SELECTION_TEXT,
        buttons=buttons,
    )


def _format_price(price_value) -> str:
    try:
        numeric_value = float(price_value)
    except (TypeError, ValueError):
        return "0"

    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.2f}".rstrip("0").rstrip(".")


def _package_row_id(category: str, package_cp: int) -> str:
    normalized_category = category.lower().replace(" ", "_")
    return f"pkg_{normalized_category}_{package_cp}"


def _build_package_rows(category: str) -> list:
    packages = get_packages(category)
    rows = []
    for item in packages:
        package_cp = item.get("package_cp")
        price_value = item.get("price")
        if package_cp is None or price_value is None:
            continue
        price_text = _format_price(price_value)
        rows.append(
            {
                "id": _package_row_id(category, int(package_cp)),
                "title": f"{int(package_cp)} CP - ${price_text}",
            }
        )
    return rows


def _send_package_list(user_phone: str, category: str) -> bool:
    rows = _build_package_rows(category)
    if not rows:
        print(f"No active package rows found for category '{category}'.")
        return send_text_message(
            user_phone,
            "No packages are available right now for this category. Please try again later.",
        )

    return send_interactive_list_message(
        to=user_phone,
        body_text=PACKAGE_HEADER,
        button_text="Select Package",
        section_title="CP Packages",
        rows=rows,
    )


def _send_login_method_buttons(user_phone: str) -> bool:
    return send_interactive_buttons_message(
        to=user_phone,
        body_text=LOGIN_METHOD_TEXT,
        buttons=[
            ("login_activision", "Activision"),
            ("login_facebook", "Facebook"),
        ],
    )


def _send_payment_method_list(user_phone: str) -> bool:
    rows = [{"id": item_id, "title": label} for item_id, label in PAYMENT_METHOD_OPTIONS]
    return send_interactive_list_message(
        to=user_phone,
        body_text=PAYMENT_METHOD_TEXT,
        button_text="Select Payment",
        section_title="USDT Payment Methods",
        rows=rows,
    )


def _set_stage(user_phone: str, stage: str, **fields: str) -> None:
    update_state(user_phone, stage=stage, **fields)
    print(f"State updated for {user_phone}: stage={stage}")


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())


def _is_admin_phone(user_phone: str) -> bool:
    if not ADMIN_PHONE:
        return False
    p1 = _normalize_phone(user_phone)
    p2 = _normalize_phone(ADMIN_PHONE)
    if not p1 or not p2:
        return False
    if p1 == p2:
        return True
    return len(p1) >= 10 and len(p2) >= 10 and p1[-10:] == p2[-10:]


def _generate_order_id() -> str:
    global _ORDER_COUNTER
    _ORDER_COUNTER += 1
    return f"AG-CODM-{_ORDER_COUNTER:06d}"


def _track_order(order_id: str, customer_phone: str) -> None:
    _ORDER_CUSTOMER_INDEX[order_id] = customer_phone


def _get_customer_phone_by_order_id(order_id: str) -> str:
    return _ORDER_CUSTOMER_INDEX.get(order_id, "")


def _is_active_order(state: dict) -> bool:
    return bool(state.get("order_id")) and state.get("order_status") in _ACTIVE_ORDER_STATUSES


def _is_restart_attempt_message(message: dict) -> bool:
    message_type = message.get("type")
    if message_type == "text":
        text_body = _extract_text_body(message).lower()
        return text_body in {"hi", "hello", "start"}

    if message_type == "interactive":
        interactive = message.get("interactive") or {}
        reply_type = interactive.get("type")
        if reply_type == "button_reply":
            button_id = ((interactive.get("button_reply") or {}).get("id") or "").strip()
            return button_id in {
                "continue_flow",
                "game_cod_mobile",
                "login_activision",
                "login_facebook",
            } or button_id.startswith("category_")
        if reply_type == "list_reply":
            list_id = ((interactive.get("list_reply") or {}).get("id") or "").strip()
            return list_id.startswith("pkg_")

    return False


def _send_active_order_protection_message(user_phone: str, state: dict) -> bool:
    order_id = state.get("order_id", "")
    current_status = state.get("order_status", "")
    message = (
        "📦 You already have an active order.\n\n"
        "Order ID:\n"
        f"{order_id}\n\n"
        "Status:\n"
        f"{current_status}\n\n"
        "Please wait until your current order is finished."
    )
    return send_text_message(user_phone, message)


def _build_admin_order_message(order_id: str, customer_phone: str, state: dict) -> str:
    lines = [
        "🆕 NEW CODM ORDER",
        "",
        "━━━━━━━━━━━━━━",
        "",
        "Order ID:",
        order_id,
        "",
        "Customer:",
        customer_phone,
        "",
        "Game:",
        state.get("game", ""),
        "",
        "Package:",
        state.get("selected_package", ""),
        "",
        "Login Method:",
        state.get("login_method", ""),
        "",
        "Email:",
        state.get("email", ""),
        "",
        "Password:",
        state.get("password", ""),
        "",
        "Ingame Name:",
        state.get("ingame_name", ""),
        "",
    ]

    if state.get("login_method") == "Facebook":
        lines.extend([
            "Recovery Codes:",
            state.get("recovery_codes", ""),
            "",
        ])

    lines.extend(
        [
            "Payment Method:",
            state.get("payment_method", ""),
            "",
            "Status:",
            "🟡 Pending Verification",
            "",
            "━━━━━━━━━━━━━━",
        ]
    )
    return "\n".join(lines)


def _send_admin_action_buttons() -> None:
    if not ADMIN_PHONE:
        print("ADMIN_PHONE is not configured. Cannot send admin action buttons.")
        return

    first_batch_ok = send_interactive_buttons_message(
        to=ADMIN_PHONE,
        body_text="Order Actions",
        buttons=_ADMIN_ACTION_BUTTONS[:2],
    )
    second_batch_ok = send_interactive_buttons_message(
        to=ADMIN_PHONE,
        body_text="Order Actions",
        buttons=_ADMIN_ACTION_BUTTONS[2:],
    )
    if first_batch_ok and second_batch_ok:
        print("Admin action buttons sent successfully.")
    else:
        print("Failed to send one or more admin action button sets.")


def _forward_screenshot_to_admin(message: dict) -> None:
    if not ADMIN_PHONE:
        print("ADMIN_PHONE is not configured. Cannot forward screenshot to admin.")
        return

    message_type = message.get("type")
    if message_type in {"image", "photo"}:
        media = message.get("image") or message.get("photo") or {}
        media_id = media.get("id", "")
        if media_id and send_image_message(ADMIN_PHONE, media_id):
            print("Forwarded payment screenshot image to admin.")
        else:
            print("Failed to forward payment screenshot image to admin.")
        return

    if message_type == "document":
        document = message.get("document") or {}
        media_id = document.get("id", "")
        if media_id and send_document_message(ADMIN_PHONE, media_id):
            print("Forwarded payment screenshot document to admin.")
        else:
            print("Failed to forward payment screenshot document to admin.")


def _send_new_order_to_admin(order_id: str, customer_phone: str, state: dict, message: dict) -> None:
    _forward_screenshot_to_admin(message)

    if not ADMIN_PHONE:
        print("ADMIN_PHONE is not configured. Cannot send order summary to admin.")
        return

    admin_message = _build_admin_order_message(order_id, customer_phone, state)
    if send_text_message(ADMIN_PHONE, admin_message):
        print("Sent complete order summary to admin.")
    else:
        print("Failed to send order summary to admin.")

    _send_admin_action_buttons()


def _build_customer_status_message(order_status: str, order_id: str) -> str:
    if order_status == "accepted":
        return (
            "✅ Payment verified.\n\n"
            "Your order is now accepted.\n\n"
            "Order ID:\n"
            f"{order_id}"
        )

    if order_status == "processing":
        return (
            "🔄 Your order is currently being processed.\n\n"
            "Order ID:\n"
            f"{order_id}"
        )

    if order_status == "completed":
        return (
            "🎉 Your COD Mobile top-up has been completed.\n\n"
            "Order ID:\n"
            f"{order_id}\n\n"
            "Thank you for choosing Alyan Gamer ❤️"
        )

    if order_status == "rejected":
        return (
            "❌ Your payment could not be verified.\n\n"
            "Please contact support.\n\n"
            "Order ID:\n"
            f"{order_id}"
        )

    return ""


def _get_latest_actionable_order_id() -> str:
    candidates = []
    for order_id, customer_phone in _ORDER_CUSTOMER_INDEX.items():
        customer_state = get_state(customer_phone)
        status = customer_state.get("order_status")
        if status in _ACTIVE_ORDER_STATUSES:
            sequence_str = order_id.rsplit("-", 1)[-1]
            try:
                sequence = int(sequence_str)
            except ValueError:
                continue
            candidates.append((sequence, order_id))

    if not candidates:
        return ""

    candidates.sort(reverse=True)
    return candidates[0][1]


def _handle_admin_action(button_id: str) -> None:
    next_status = _ADMIN_ACTION_TO_STATUS.get(button_id)
    if not next_status:
        return

    order_id = _get_latest_actionable_order_id()
    if not order_id:
        if ADMIN_PHONE:
            send_text_message(ADMIN_PHONE, "No active order found for this action.")
        print("No active order found for admin action.")
        return

    customer_phone = _get_customer_phone_by_order_id(order_id)
    if not customer_phone:
        if ADMIN_PHONE:
            send_text_message(ADMIN_PHONE, "Unable to find customer for selected order.")
        print(f"No customer mapped for order {order_id}.")
        return

    _set_stage(customer_phone, next_status, order_status=next_status)
    customer_message = _build_customer_status_message(next_status, order_id)
    if customer_message:
        send_text_message(customer_phone, customer_message)

    if ADMIN_PHONE:
        send_text_message(
            ADMIN_PHONE,
            f"Order {order_id} updated to {next_status} for customer {customer_phone}.",
        )


def _handle_admin_interactive_reply(message: dict) -> None:
    interactive = message.get("interactive") or {}
    reply_type = interactive.get("type")
    if reply_type != "button_reply":
        print("Admin message is not a button reply; ignoring.")
        return

    button_id = ((interactive.get("button_reply") or {}).get("id") or "").strip()
    if button_id not in _ADMIN_ACTION_TO_STATUS:
        print("Admin button id is not an order action; ignoring.")
        return

    _handle_admin_action(button_id)


def _extract_text_body(message: dict) -> str:
    text = message.get("text") or {}
    return (text.get("body") or "").strip()


def _is_image_document(message: dict) -> bool:
    document = message.get("document") or {}
    mime_type = (document.get("mime_type") or "").lower()
    return mime_type.startswith("image/")


def _payment_label_from_id(payment_id: str) -> str:
    for item_id, label in PAYMENT_METHOD_OPTIONS:
        if item_id == payment_id:
            return label
    return ""


def _category_from_button_id(button_id: str) -> str:
    if not button_id.startswith("category_"):
        return ""

    normalized = button_id.replace("category_", "", 1)
    for category in get_categories():
        if category.lower().replace(" ", "_") == normalized:
            return category
    return ""


def _parse_package_id(package_id: str):
    if not package_id.startswith("pkg_"):
        return None, None

    remainder = package_id[4:]
    if "_" not in remainder:
        return None, None

    category_part, package_cp_part = remainder.rsplit("_", 1)
    if not package_cp_part.isdigit():
        return None, None

    category = category_part.replace("_", " ").title()
    return category, int(package_cp_part)


def _send_payment_method_prompt(user_phone: str) -> None:
    if _send_payment_method_list(user_phone):
        print("Payment method list sent successfully.")
    else:
        print("Failed to send payment method list.")


def _build_admin_payment_help_notification(user_phone: str, state: dict) -> str:
    selected_package = state.get("selected_package", "")
    login_method = state.get("login_method", "")
    return (
        "ADMIN NOTIFICATION\n"
        f"Customer Phone: {user_phone}\n"
        f"Selected Package: {selected_package}\n"
        f"Login Method: {login_method}\n"
        "Reason:\n"
        "Customer doesn't have USDT payment methods."
    )


def _notify_admin_payment_help(user_phone: str, state: dict) -> None:
    notification = _build_admin_payment_help_notification(user_phone, state)
    print(notification)
    if ADMIN_PHONE:
        if send_text_message(ADMIN_PHONE, notification):
            print("Sent payment-help notification to admin.")
        else:
            print("Failed to send payment-help notification to admin.")


def _handle_activision_text_step(user_phone: str, state: dict, text_body: str) -> bool:
    stage = state.get("stage")

    if stage == "awaiting_activision_details":
        parsed_details = _parse_account_details(text_body)
        missing_fields = _get_missing_fields("Activision", parsed_details)
        if missing_fields:
            selected_package = state.get("selected_package", "")
            missing_line = ", ".join(missing_fields)
            retry_message = (
                f"❌ Missing required field(s): {missing_line}\n\n"
                f"{ACCOUNT_DETAILS_ONE_MESSAGE_HINT}\n\n"
                f"{_build_activision_template(selected_package)}"
            )
            print(f"Missing Activision fields: {missing_line}")
            return send_text_message(user_phone, retry_message)

        _set_stage(
            user_phone,
            "awaiting_payment_method",
            email=parsed_details.get("email", ""),
            password=parsed_details.get("password", ""),
            ingame_name=parsed_details.get("ingame_name", ""),
            recovery_codes="",
        )
        print("Collected Activision details in one message")
        if not send_text_message(
            user_phone,
            "✅ Activision account information received.\n\nPreparing next step...",
        ):
            return False

        _send_payment_method_prompt(user_phone)
        return True

    return False


def _handle_facebook_text_step(user_phone: str, state: dict, text_body: str) -> bool:
    stage = state.get("stage")

    if stage == "awaiting_facebook_details":
        parsed_details = _parse_account_details(text_body)
        missing_fields = _get_missing_fields("Facebook", parsed_details)
        if missing_fields:
            selected_package = state.get("selected_package", "")
            missing_line = ", ".join(missing_fields)
            retry_message = (
                f"❌ Missing required field(s): {missing_line}\n\n"
                f"{ACCOUNT_DETAILS_ONE_MESSAGE_HINT}\n\n"
                f"{_build_facebook_template(selected_package)}"
            )
            print(f"Missing Facebook fields: {missing_line}")
            return send_text_message(user_phone, retry_message)

        _set_stage(
            user_phone,
            "awaiting_payment_method",
            email=parsed_details.get("email", ""),
            password=parsed_details.get("password", ""),
            ingame_name=parsed_details.get("ingame_name", ""),
            recovery_codes=parsed_details.get("recovery_codes", ""),
        )
        print("Collected Facebook details in one message")
        if not send_text_message(
            user_phone,
            "✅ Facebook account information received.\n\nPreparing next step...",
        ):
            return False

        _send_payment_method_prompt(user_phone)
        return True

    return False


def _handle_text_reply(user_phone: str, state: dict, message: dict) -> None:
    text_body = _extract_text_body(message)
    if not text_body:
        print("Empty text message received; no state transition.")
        return

    stage = state.get("stage")
    if stage == "awaiting_payment_screenshot":
        print("Text received while awaiting payment screenshot.")
        send_text_message(user_phone, PAYMENT_SCREENSHOT_REQUIRED_TEXT)
        return

    if stage == "awaiting_admin_payment_help":
        print("Customer is waiting for admin payment help.")
        send_text_message(
            user_phone,
            "Our support team is already notified. Please wait for assistance.",
        )
        return

    if stage in {"pending_verification", "accepted", "processing"}:
        print("Payment verification already pending.")
        _send_active_order_protection_message(user_phone, state)
        return

    login_method = state.get("login_method")
    if login_method == "Activision":
        if _handle_activision_text_step(user_phone, state, text_body):
            return

    if login_method == "Facebook":
        if _handle_facebook_text_step(user_phone, state, text_body):
            return

    print("Text message received outside expected input step.")


def _handle_payment_method_selection(user_phone: str, state: dict, payment_id: str) -> bool:
    payment_label = _payment_label_from_id(payment_id)
    if not payment_label:
        return False

    if state.get("stage") != "awaiting_payment_method":
        print("Payment method selected out of sequence.")
        send_text_message(user_phone, STEP_GUARD_TEXT)
        return True

    if payment_id == "payment_binance":
        _set_stage(
            user_phone,
            "awaiting_payment_screenshot",
            payment_method=payment_label,
        )
        return send_text_message(user_phone, BINANCE_PAYMENT_TEXT)

    if payment_id == "payment_bybit":
        _set_stage(
            user_phone,
            "awaiting_payment_screenshot",
            payment_method=payment_label,
        )
        return send_text_message(user_phone, BYBIT_PAYMENT_TEXT)

    if payment_id == "payment_tron_trc20":
        _set_stage(
            user_phone,
            "awaiting_payment_screenshot",
            payment_method=payment_label,
        )
        return send_text_message(user_phone, TRON_PAYMENT_TEXT)

    if payment_id == "payment_no_method":
        _set_stage(
            user_phone,
            "awaiting_admin_payment_help",
            payment_method=payment_label,
        )
        _notify_admin_payment_help(user_phone, get_state(user_phone))
        return send_text_message(user_phone, NO_PAYMENT_METHOD_TEXT)

    return False


def _handle_media_reply(user_phone: str, state: dict, message: dict) -> None:
    stage = state.get("stage")
    if stage != "awaiting_payment_screenshot":
        print("Media received outside screenshot stage.")
        send_text_message(user_phone, STEP_GUARD_TEXT)
        return

    message_type = message.get("type")
    is_supported = message_type in {"image", "photo"} or (
        message_type == "document" and _is_image_document(message)
    )
    if not is_supported:
        print("Unsupported media type for payment screenshot.")
        send_text_message(user_phone, PAYMENT_SCREENSHOT_REQUIRED_TEXT)
        return

    media_object = message.get("image") or message.get("photo") or message.get("document") or {}
    media_id = media_object.get("id", "")
    order_id = _generate_order_id()
    _set_stage(
        user_phone,
        "pending_verification",
        order_id=order_id,
        order_status="pending_verification",
        payment_screenshot_media_id=media_id,
    )
    _track_order(order_id, user_phone)
    print("Payment screenshot received.")
    _send_new_order_to_admin(order_id, user_phone, get_state(user_phone), message)
    send_text_message(user_phone, PAYMENT_SCREENSHOT_RECEIVED_TEXT)


def _handle_interactive_reply(user_phone: str, message: dict) -> None:
    interactive = message.get("interactive") or {}
    reply_type = interactive.get("type")
    state = get_state(user_phone)
    current_stage = state.get("stage")

    if current_stage == "awaiting_payment_screenshot":
        print("Interactive message received while awaiting payment screenshot.")
        send_text_message(user_phone, PAYMENT_SCREENSHOT_REQUIRED_TEXT)
        return

    if reply_type == "button_reply":
        button_reply = interactive.get("button_reply") or {}
        button_id = button_reply.get("id", "")
        button_title = button_reply.get("title", "")
        print(f"Button reply received: id={button_id}, title={button_title}")

        if button_id in _ADMIN_ACTION_TO_STATUS:
            if not _is_admin_phone(user_phone):
                print("Customer attempted admin action button.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            _handle_admin_action(button_id)
            return

        if button_id == "continue_flow":
            if current_stage != "awaiting_continue":
                print("Continue clicked out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            _set_stage(user_phone, "game_selection")
            if _send_game_button(user_phone):
                print("Game selection button sent successfully.")
            else:
                print("Failed to send game selection button.")
            return

        if button_id == "game_cod_mobile":
            if current_stage != "game_selection":
                print("Game selected out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            _set_stage(user_phone, "awaiting_category", game="COD Mobile")
            if _send_category_buttons(user_phone):
                print("Category selection buttons sent successfully.")
            else:
                print("Failed to send category selection buttons.")
            return

        selected_category = _category_from_button_id(button_id)
        if selected_category:
            if current_stage != "awaiting_category":
                print("Category selected out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            _set_stage(user_phone, "package_selection", category=selected_category)
            if _send_package_list(user_phone, selected_category):
                print(f"Package list sent for category: {selected_category}")
            else:
                print(f"Failed to send package list for category: {selected_category}")
            return

        if button_id == "login_activision":
            if current_stage != "awaiting_login_method":
                print("Login method selected out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            selected_package = state.get("selected_package", "")
            _set_stage(user_phone, "awaiting_activision_details", login_method="Activision")
            print("Login Method: Activision")
            if send_text_message(user_phone, _build_activision_template(selected_package)):
                print("Sent Activision one-message template.")
            else:
                print("Failed to send Activision template.")
            return

        if button_id == "login_facebook":
            if current_stage != "awaiting_login_method":
                print("Login method selected out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return
            selected_package = state.get("selected_package", "")
            _set_stage(user_phone, "awaiting_facebook_details", login_method="Facebook")
            print("Login Method: Facebook")
            if send_text_message(user_phone, _build_facebook_template(selected_package)):
                print("Sent Facebook one-message template.")
            else:
                print("Failed to send Facebook template.")
            return

    if reply_type == "list_reply":
        list_reply = interactive.get("list_reply") or {}
        list_id = list_reply.get("id", "")
        list_title = list_reply.get("title", "")

        if _handle_payment_method_selection(user_phone, state, list_id):
            return

        package_category, package_cp = _parse_package_id(list_id)
        if package_category and package_cp is not None:
            if current_stage != "package_selection":
                print("Package selected out of sequence.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return

            expected_category = state.get("category", "")
            if expected_category and expected_category.lower() != package_category.lower():
                print("Package category mismatch detected.")
                send_text_message(user_phone, STEP_GUARD_TEXT)
                return

            selected_price = get_price(package_cp)
            if selected_price is None:
                print(f"No active price found for package_cp={package_cp}")
                send_text_message(
                    user_phone,
                    "Selected package is currently unavailable. Please choose another package.",
                )
                return

            price_text = _format_price(selected_price)
            selected_package = f"{package_cp} CP"
            selected_package_with_price = f"{selected_package} - ${price_text}"

            _set_stage(
                user_phone,
                "package_selected",
                selected_package=selected_package_with_price,
                selected_price=price_text,
                selected_category=package_category,
            )
            print(f"Customer selected package: {selected_package_with_price}")
            confirmation = (
                "✅ Package Selected\n\n"
                f"Package:\n{selected_package}\n\n"
                f"Price:\n${price_text}\n\n"
                "Preparing next step..."
            )
            if send_text_message(user_phone, confirmation):
                print("Package confirmation sent successfully.")
            else:
                print("Failed to send package confirmation.")

            _set_stage(user_phone, "awaiting_login_method")
            if _send_login_method_buttons(user_phone):
                print("Login method buttons sent successfully.")
            else:
                print("Failed to send login method buttons.")
            return

    print("Interactive reply did not match any sprint action.")


def handle_order_flow_message(user_phone: str, message: dict) -> None:
    message_type = message.get("type")
    state = get_state(user_phone)
    print(f"Current state for {user_phone}: {state}")

    if _is_admin_phone(user_phone):
        if message_type == "interactive":
            _handle_admin_interactive_reply(message)
        else:
            print("Ignoring non-interactive admin message.")
        return

    if _is_active_order(state) and _is_restart_attempt_message(message):
        print("Blocked restart attempt due to active order.")
        _send_active_order_protection_message(user_phone, state)
        return

    if not state.get("stage"):
        if _send_welcome_continue(user_phone):
            _set_stage(user_phone, "awaiting_continue")
            print("Welcome continue button sent successfully.")
        else:
            print("Failed to send welcome continue button.")
        return

    if message_type == "interactive":
        _handle_interactive_reply(user_phone, message)
        return

    if message_type == "text":
        _handle_text_reply(user_phone, state, message)
        return

    if message_type in {"image", "photo", "document"}:
        _handle_media_reply(user_phone, state, message)
        return

    if state.get("stage") == "awaiting_payment_screenshot":
        print("Unsupported message type while awaiting payment screenshot.")
        send_text_message(user_phone, PAYMENT_SCREENSHOT_REQUIRED_TEXT)
        return

    print("Non-text/non-interactive message received during active flow; ignoring.")