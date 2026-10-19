from fastapi import WebSocket


async def reject_websocket(websocket: WebSocket, code: int, reason: str) -> None:
    """Refuse a websocket with an application close code (4xxx).

    Accepts first: closing before accept() becomes an HTTP 403 on the
    handshake, and clients never see the close code they need to react to
    (4401 -> sign in again, 4403 -> suspended).
    """
    await websocket.accept()
    await websocket.close(code=code, reason=reason)
