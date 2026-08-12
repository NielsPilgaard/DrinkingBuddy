import uuid

from fastapi import WebSocket

MAX_PARTICIPANTS_PER_CALL = 2


class CallFullError(Exception):
    pass


class CallRegistry:
    """Tracks the (at most two) live websockets per call_id.

    In-process, in-memory: signaling is a single-VPS, single-worker
    process (per docs/tech-stack.md), and a call only ever has two
    participants, so there's no need for Redis-backed shared state here
    the way the matching queue needs it.
    """

    def __init__(self) -> None:
        self._calls: dict[str, dict[uuid.UUID, WebSocket]] = {}

    def join(self, call_id: str, user_id: uuid.UUID, websocket: WebSocket) -> WebSocket | None:
        """Registers websocket for user_id, returning any previous socket that was replaced."""
        participants = self._calls.setdefault(call_id, {})
        previous = participants.get(user_id)
        if previous is None and len(participants) >= MAX_PARTICIPANTS_PER_CALL:
            raise CallFullError
        participants[user_id] = websocket
        return previous

    def leave(self, call_id: str, user_id: uuid.UUID, websocket: WebSocket) -> bool:
        """Removes user_id only if websocket is still its registered socket.

        Returns True iff this call actually removed the active socket - False
        when `websocket` had already been replaced (e.g. by a reconnect), so
        callers can distinguish a genuine departure from stale cleanup.
        """
        participants = self._calls.get(call_id)
        if participants is None:
            return False
        if participants.get(user_id) is not websocket:
            return False
        participants.pop(user_id, None)
        if not participants:
            self._calls.pop(call_id, None)
        return True

    def peer_socket(self, call_id: str, user_id: uuid.UUID) -> WebSocket | None:
        participants = self._calls.get(call_id)
        if participants is None:
            return None
        for peer_id, socket in participants.items():
            if peer_id != user_id:
                return socket
        return None


call_registry = CallRegistry()
