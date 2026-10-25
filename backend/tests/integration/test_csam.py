import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

import app.csam.service as csam_service
from app.chat_safety.service import scan_chat_message
from app.config import settings
from app.csam.service import purge_expired_cases, read_evidence
from app.models.csam import CsamAuditLog, CsamCase
from app.models.user import User
from app.moderation.service import is_suspended, submit_report

pytestmark = pytest.mark.integration

_OFFICER = {"X-Csam-Secret": settings.csam_moderation_secret, "X-Actor": "niels"}


@pytest.fixture(autouse=True)
def oncall_emails(monkeypatch) -> list[tuple[str, str, str]]:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        csam_service,
        "send_csam_case_opened_email",
        lambda to, case_id, source: sent.append((to, case_id, source)),
    )
    return sent


async def _make_user(db_session, email: str) -> uuid.UUID:
    user = User(email=email, birthdate=datetime(2000, 1, 1, tzinfo=UTC).date())
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user.id


async def _cases(db_session) -> list[CsamCase]:
    return list((await db_session.execute(select(CsamCase))).scalars().all())


async def _audit_actions(db_session) -> list[str]:
    result = await db_session.execute(select(CsamAuditLog.action).order_by(CsamAuditLog.created_at))
    return list(result.scalars().all())


async def _open_case_via_report(db_session, tag: str) -> tuple[uuid.UUID, CsamCase]:
    reporter = await _make_user(db_session, f"{tag}-reporter@example.com")
    reported = await _make_user(db_session, f"{tag}-reported@example.com")
    await submit_report(db_session, reporter, reported, f"call-{tag}", "csam")
    (case,) = await _cases(db_session)
    return reported, case


# --- report routing --------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_csam_report_opens_case_and_suspends(db_session, oncall_emails):
    reported, case = await _open_case_via_report(db_session, "route")

    assert case.status == "open"
    assert case.source == "user_report"
    assert case.legal_hold is False
    # One report is below the generic 3-in-24h threshold - the suspension
    # comes from the CSAM path, not the breaker.
    assert await is_suspended(db_session, reported) is True
    assert oncall_emails == [(settings.csam_oncall_email, str(case.id), "user_report")]
    assert await _audit_actions(db_session) == ["open_case", "notify_oncall"]


@pytest.mark.asyncio
async def test_non_csam_report_opens_no_case(db_session, oncall_emails):
    reporter = await _make_user(db_session, "plain-reporter@example.com")
    reported = await _make_user(db_session, "plain-reported@example.com")

    await submit_report(db_session, reporter, reported, "call-plain", "nudity")

    assert await _cases(db_session) == []
    assert oncall_emails == []


@pytest.mark.asyncio
async def test_evidence_is_encrypted_and_includes_flagged_chat(db_session):
    reporter = await _make_user(db_session, "ev-reporter@example.com")
    reported = await _make_user(db_session, "ev-reported@example.com")
    await scan_chat_message(
        db_session,
        call_session_id="call-ev",
        sender_id=reported,
        recipient_id=reporter,
        text="add me on snapchat",
    )

    await submit_report(db_session, reporter, reported, "call-ev", "csam")
    (case,) = await _cases(db_session)

    assert b"ev-reported@example.com" not in case.evidence_ciphertext
    evidence = read_evidence(case)
    assert evidence["reported_user"]["email"] == "ev-reported@example.com"
    assert evidence["reports"][0]["reason"] == "csam"
    assert [m["text"] for m in evidence["flagged_messages"]] == ["add me on snapchat"]


@pytest.mark.asyncio
async def test_second_csam_report_for_same_call_does_not_duplicate_case(db_session, oncall_emails):
    reporter_a = await _make_user(db_session, "dup-a@example.com")
    reporter_b = await _make_user(db_session, "dup-b@example.com")
    reported = await _make_user(db_session, "dup-reported@example.com")

    await submit_report(db_session, reporter_a, reported, "call-dup", "csam")
    await submit_report(db_session, reporter_b, reported, "call-dup", "csam")

    assert len(await _cases(db_session)) == 1
    assert len(oncall_emails) == 1
    assert "additional_trigger" in await _audit_actions(db_session)


@pytest.mark.asyncio
async def test_oncall_email_failure_does_not_fail_report(db_session, monkeypatch):
    def _boom(*_args):
        raise OSError("smtp down")

    monkeypatch.setattr(csam_service, "send_csam_case_opened_email", _boom)

    _, case = await _open_case_via_report(db_session, "smtp")

    failed = await db_session.execute(
        select(CsamAuditLog).where(
            CsamAuditLog.action == "notify_oncall", CsamAuditLog.case_id == case.id
        )
    )
    assert failed.scalar_one().success is False


@pytest.mark.asyncio
async def test_report_endpoint_accepts_csam_reason(client, db_session):
    # An unknown reason fails body validation with 422 before the endpoint
    # runs; reaching the auth check (401) proves "csam" is an accepted reason.
    response = await client.post(
        "/report",
        json={"reported_id": str(uuid.uuid4()), "call_session_id": "c", "reason": "csam"},
    )
    assert response.status_code == 401


# --- officer endpoints -----------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoints_require_csam_secret_and_actor(client, db_session):
    await _open_case_via_report(db_session, "gate")

    no_secret = await client.get("/moderation/csam/cases")
    assert no_secret.status_code == 401

    wrong_secret = await client.get(
        "/moderation/csam/cases", headers={"X-Csam-Secret": "wrong", "X-Actor": "x"}
    )
    assert wrong_secret.status_code == 401

    no_actor = await client.get(
        "/moderation/csam/cases", headers={"X-Csam-Secret": settings.csam_moderation_secret}
    )
    assert no_actor.status_code == 400

    ok = await client.get("/moderation/csam/cases", headers=_OFFICER)
    assert ok.status_code == 200
    assert len(ok.json()) == 1
    assert "evidence_ciphertext" not in ok.json()[0]


@pytest.mark.asyncio
async def test_view_evidence_is_audited_with_actor(client, db_session):
    _, case = await _open_case_via_report(db_session, "view")

    response = await client.get(f"/moderation/csam/cases/{case.id}/evidence", headers=_OFFICER)

    assert response.status_code == 200
    assert response.json()["evidence"]["call_session_id"] == "call-view"
    audit = await db_session.execute(
        select(CsamAuditLog).where(CsamAuditLog.action == "view_evidence")
    )
    row = audit.scalar_one()
    assert row.actor == "csam:niels"
    assert row.case_id == case.id


@pytest.mark.asyncio
async def test_dismiss_lifts_precautionary_suspension(client, db_session):
    reported, case = await _open_case_via_report(db_session, "dismiss")

    response = await client.post(
        f"/moderation/csam/cases/{case.id}/dismiss",
        headers=_OFFICER,
        json={"reason": "griefing report, verified adult"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"
    assert await is_suspended(db_session, reported) is False

    again = await client.post(
        f"/moderation/csam/cases/{case.id}/dismiss", headers=_OFFICER, json={"reason": "x"}
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_mark_reported_sets_legal_hold_and_keeps_suspension(client, db_session):
    reported, case = await _open_case_via_report(db_session, "reported")

    response = await client.post(
        f"/moderation/csam/cases/{case.id}/reported",
        headers=_OFFICER,
        json={"external_reference": "NC3-2026-0001"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "reported"
    assert body["legal_hold"] is True
    assert body["external_reference"] == "NC3-2026-0001"
    assert await is_suspended(db_session, reported) is True


@pytest.mark.asyncio
async def test_escalate_chat_flag_opens_case(client, db_session, oncall_emails):
    sender = await _make_user(db_session, "esc-sender@example.com")
    recipient = await _make_user(db_session, "esc-recipient@example.com")
    await scan_chat_message(
        db_session,
        call_session_id="call-esc",
        sender_id=sender,
        recipient_id=recipient,
        text="add me on snapchat",
    )
    flags = await client.get(
        "/moderation/chat-safety/flags",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )
    flag_id = flags.json()[0]["id"]

    response = await client.post(
        f"/moderation/chat-safety/flags/{flag_id}/escalate-csam",
        headers={"X-Moderation-Secret": settings.chat_safety_moderation_secret},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "chat_flag"
    assert response.json()["reported_id"] == str(sender)
    assert await is_suspended(db_session, sender) is True
    assert [source for _, _, source in oncall_emails] == ["chat_flag"]


# --- retention -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retention_sweep_respects_legal_hold(client, db_session):
    _, expired = await _open_case_via_report(db_session, "expired")
    past = datetime.now(UTC) - timedelta(days=1)
    await db_session.execute(update(CsamCase).values(retain_until=past))
    await db_session.commit()

    hold = await client.put(
        f"/moderation/csam/cases/{expired.id}/legal-hold",
        headers=_OFFICER,
        json={"active": True, "reason": "police preservation request"},
    )
    assert hold.status_code == 200

    assert await purge_expired_cases(db_session) == 0
    assert len(await _cases(db_session)) == 1

    await client.put(
        f"/moderation/csam/cases/{expired.id}/legal-hold",
        headers=_OFFICER,
        json={"active": False, "reason": "hold released by counsel"},
    )

    assert await purge_expired_cases(db_session) == 1
    assert await _cases(db_session) == []
    actions = await _audit_actions(db_session)
    assert actions.count("retention_sweep") == 2
    assert {"legal_hold_on", "legal_hold_off"} <= set(actions)


@pytest.mark.asyncio
async def test_retention_sweep_keeps_unexpired_cases(db_session):
    await _open_case_via_report(db_session, "fresh")

    assert await purge_expired_cases(db_session) == 0
    assert len(await _cases(db_session)) == 1
