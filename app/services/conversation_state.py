from typing import Dict


# In-memory conversation state for sprint flow; can be swapped with DB later.
_CONVERSATION_STATE: Dict[str, Dict[str, str]] = {}


def get_state(user_phone: str) -> Dict[str, str]:
    return _CONVERSATION_STATE.get(user_phone, {})


def set_state(user_phone: str, state: Dict[str, str]) -> None:
    _CONVERSATION_STATE[user_phone] = state


def update_state(user_phone: str, **fields: str) -> Dict[str, str]:
    current = get_state(user_phone).copy()
    current.update(fields)
    set_state(user_phone, current)
    return current