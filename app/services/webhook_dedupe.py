from threading import Lock


_PROCESSED_MESSAGE_IDS = set()
_LOCK = Lock()


def is_duplicate_message(message_id: str) -> bool:
    if not message_id:
        return False

    with _LOCK:
        if message_id in _PROCESSED_MESSAGE_IDS:
            return True
        _PROCESSED_MESSAGE_IDS.add(message_id)
        return False