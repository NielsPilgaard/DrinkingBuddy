import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select, update

import app.auth.service as auth_service
from app.chat_safety.matcher import AGE_UNDER_18_CATEGORY, CONTACT_INFO_CATEGORY, MEETUP_CATEGORY
from app.chat_safety.service import decrypt_flag, purge_expired_flags, scan_chat_message
from app.config import settings
from app.models.chat_safety import ChatSafetyAuditLog, FlaggedMessage
from app.models.user import User
from app.signaling.session import call_id_for_pair

pytestmark = pytest.mark.integration


async def _make_user(db_session, email: str) -> uuid.UUID:
    user = User(email=email, birthdate=datetime(2000, 1, 1, tzinfo=UTC).date())
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


async def _signup_and_get_token(client, monkeypatch, email: str) -> tuple[str, uuid.UUID]:
    sent: list[str] = []
    monkeypatch.setattr(
        auth_service, "send_magic_link_email", lambda email, link: sent.append(link)
    )
    await client.post("/auth/request-link", json={"email": email, "birthdate": "2000-01-01"})
    token = parse_qs(urlparse(sent[-1]).query)["token"][0]
    verify_response = await client.get("/auth/verify", params={"token": token})
    body = verify_response.json()
    return body["session_token"], uuid.UUID(body["user_id"])


# --- service-level flag flow -------------------------------------------------


@pytest.mark.asyncio
async def test_meetup_phrase_flags_silently(db_session):
    sender = await _make_user(db_session, "meetup-sender@example.com")
    recipient = await _make_user(db_session, "meetup-recipient@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-meetup",
        sender_id=sender,
        recipient_id=recipient,
        text="let's meet up this weekend",
    )

    result = await db_session.execute(select(FlaggedMessage))
    flags = result.scalars().all()
    assert len(flags) == 1
    assert flags[0].category == MEETUP_CATEGORY
    assert flags[0].sender_id == sender
    assert await decrypt_flag(flags[0]) == "let's meet up this weekend"


@pytest.mark.asyncio
async def test_contact_info_sharing_flags(db_session):
    sender = await _make_user(db_session, "contact-sender@example.com")
    recipient = await _make_user(db_session, "contact-recipient@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-contact",
        sender_id=sender,
        recipient_id=recipient,
        text="find me on instagram",
    )

    result = await db_session.execute(select(FlaggedMessage))
    flags = result.scalars().all()
    assert len(flags) == 1
    assert flags[0].category == CONTACT_INFO_CATEGORY


@pytest.mark.asyncio
async def test_age_question_alone_does_not_flag(db_session):
    sender = await _make_user(db_session, "asker@example.com")
    recipient = await _make_user(db_session, "askee@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-age-1",
        sender_id=sender,
        recipient_id=recipient,
        text="how old are you?",
    )

    result = await db_session.execute(select(FlaggedMessage))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_age_question_then_under_18_answer_flags(db_session):
    asker = await _make_user(db_session, "asker2@example.com")
    answerer = await _make_user(db_session, "answerer2@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-age-2",
        sender_id=asker,
        recipient_id=answerer,
        text="how old are you?",
    )
    await scan_chat_message(
        db_session,
        call_session_id="call-age-2",
        sender_id=answerer,
        recipient_id=asker,
        text="im 15",
    )

    result = await db_session.execute(select(FlaggedMessage))
    flags = result.scalars().all()
    assert len(flags) == 1
    assert flags[0].category == AGE_UNDER_18_CATEGORY
    assert flags[0].sender_id == answerer


@pytest.mark.asyncio
async def test_age_question_then_adult_answer_does_not_flag(db_session):
    asker = await _make_user(db_session, "asker3@example.com")
    answerer = await _make_user(db_session, "answerer3@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-age-3",
        sender_id=asker,
        recipient_id=answerer,
        text="how old are you?",
    )
    await scan_chat_message(
        db_session,
        call_session_id="call-age-3",
        sender_id=answerer,
        recipient_id=asker,
        text="25",
    )

    result = await db_session.execute(select(FlaggedMessage))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_unrelated_message_does_not_flag(db_session):
    sender = await _make_user(db_session, "plain-sender@example.com")
    recipient = await _make_user(db_session, "plain-recipient@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-plain",
        sender_id=sender,
        recipient_id=recipient,
        text="what's your favorite beer?",
    )

    result = await db_session.execute(select(FlaggedMessage))
    assert result.scalars().all() == []


# --- websocket relay wiring ---------------------------------------------------


@pytest.mark.asyncio
async def test_flagged_chat_message_still_relays_to_peer_and_stays_silent(ws_client, monkeypatch):
    """A filter hit must not surface any indication to either user, and must
    not interrupt the normal chat relay (tasks/13-chat-safety-filters.md)."""
    token_a, user_a_id = await _signup_and_get_token(ws_client, monkeypatch, "flag-a@example.com")
    token_b, user_b_id = await _signup_and_get_token(ws_client, monkeypatch, "flag-b@example.com")
    call_id = call_id_for_pair(user_a_id, user_b_id)

    async with ws_client.websocket(f"/signaling/ws?token={token_a}&call_id={call_id}") as ws_a:
        await ws_a.receive_json()  # turn creds

        async with ws_client.websocket(f"/signaling/ws?token={token_b}&call_id={call_id}") as ws_b:
            await ws_b.receive_json()  # turn creds
            await ws_b.receive_json()  # peer_joined
            await ws_a.receive_json()  # peer_joined

            await ws_a.send_json({"type": "chat", "text": "let's meet up irl"})
            chat = await ws_b.receive_json()
            assert chat["message"]["type"] == "chat"
            assert chat["message"]["text"] == "let's meet up irl"


# --- moderator endpoints -------------------------------------------------------


@pytest.mark.asyncio
async def test_list_flags_requires_moderation_secret(client, db_session):
    sender = await _make_user(db_session, "gate-sender@example.com")
    recipient = await _make_user(db_session, "gate-recipient@example.com")
    await scan_chat_message(
        db_session,
        call_session_id="call-gate",
        sender_id=sender,
        recipient_id=recipient,
        text="add me on snapchat",
    )

    unauthorized = await client.get("/moderation/chat-safety/flags")
    assert unauthorized.status_code == 401

    authorized = await client.get(
        "/moderation/chat-safety/flags",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    assert authorized.status_code == 200
    assert len(authorized.json()) == 1


@pytest.mark.asyncio
async def test_get_flag_detail_decrypts_and_logs_access(client, db_session):
    sender = await _make_user(db_session, "detail-sender@example.com")
    recipient = await _make_user(db_session, "detail-recipient@example.com")
    await scan_chat_message(
        db_session,
        call_session_id="call-detail",
        sender_id=sender,
        recipient_id=recipient,
        text="call me at 87654321",
    )
    flag_id = (await db_session.execute(select(FlaggedMessage.id))).scalar_one()

    response = await client.get(
        f"/moderation/chat-safety/flags/{flag_id}",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "call me at 87654321"

    audit = await db_session.execute(
        select(ChatSafetyAuditLog).where(ChatSafetyAuditLog.action == "view_flag")
    )
    assert len(audit.scalars().all()) == 1


@pytest.mark.asyncio
async def test_pattern_upsert_rejects_invalid_regex(client):
    response = await client.put(
        "/moderation/chat-safety/patterns",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
        json={"slug": "test-rule", "category": "meetup_proposal", "pattern": "("},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pattern_upsert_versions_and_rollback_works(client):
    v1 = await client.put(
        "/moderation/chat-safety/patterns",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
        json={"slug": "custom-rule", "category": "meetup_proposal", "pattern": r"\bfoo\b"},
    )
    assert v1.status_code == 200
    assert v1.json()["version"] == 1

    v2 = await client.put(
        "/moderation/chat-safety/patterns",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
        json={"slug": "custom-rule", "category": "meetup_proposal", "pattern": r"\bbar\b"},
    )
    assert v2.status_code == 200
    assert v2.json()["version"] == 2

    active = await client.get(
        "/moderation/chat-safety/patterns",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    active_rows = [row for row in active.json() if row["slug"] == "custom-rule"]
    assert len(active_rows) == 1
    assert active_rows[0]["version"] == 2

    rollback = await client.post(
        "/moderation/chat-safety/patterns/custom-rule/rollback/1",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    assert rollback.status_code == 200
    assert rollback.json()["version"] == 1

    active_after = await client.get(
        "/moderation/chat-safety/patterns",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    active_after_rows = [row for row in active_after.json() if row["slug"] == "custom-rule"]
    assert len(active_after_rows) == 1
    assert active_after_rows[0]["version"] == 1


# --- retention sweep -----------------------------------------------------------


@pytest.mark.asyncio
async def test_retention_sweep_purges_only_expired_rows(db_session):
    sender = await _make_user(db_session, "retain-sender@example.com")
    recipient = await _make_user(db_session, "retain-recipient@example.com")

    await scan_chat_message(
        db_session,
        call_session_id="call-retain-fresh",
        sender_id=sender,
        recipient_id=recipient,
        text="let's meet up",
    )
    await scan_chat_message(
        db_session,
        call_session_id="call-retain-stale",
        sender_id=sender,
        recipient_id=recipient,
        text="find me on tiktok",
    )

    stale_cutoff = datetime.now(UTC) - timedelta(
        days=settings.chat_safety_retention_days,
        hours=settings.chat_safety_retention_grace_hours + 1,
    )
    await db_session.execute(
        update(FlaggedMessage)
        .where(FlaggedMessage.call_session_id == "call-retain-stale")
        .values(created_at=stale_cutoff)
    )
    await db_session.commit()

    purged = await purge_expired_flags(db_session)
    assert purged == 1

    remaining = await db_session.execute(select(FlaggedMessage))
    remaining_sessions = {row.call_session_id for row in remaining.scalars().all()}
    assert remaining_sessions == {"call-retain-fresh"}

    audit = await db_session.execute(
        select(ChatSafetyAuditLog).where(ChatSafetyAuditLog.action == "retention_sweep")
    )
    audit_rows = audit.scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].success is True
