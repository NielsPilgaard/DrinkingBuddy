from datetime import UTC, date, datetime, timedelta

import app.auth.service as auth_service
from app.auth.security import generate_token, hash_token
from app.auth.service import _is_underage

# Fixed, non-leap reference date so year-17/-18 arithmetic never lands on Feb 29.
REFERENCE_TODAY = date(2025, 6, 15)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(
            REFERENCE_TODAY.year, REFERENCE_TODAY.month, REFERENCE_TODAY.day, tzinfo=tz or UTC
        )


def _freeze_today(monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "datetime", _FrozenDatetime)


def test_generate_token_is_unique_and_urlsafe() -> None:
    a, b = generate_token(), generate_token()
    assert a != b
    assert all(c.isalnum() or c in "-_" for c in a)


def test_hash_token_is_deterministic_and_one_way() -> None:
    token = generate_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token


def test_is_underage_true_for_17_year_old(monkeypatch) -> None:
    _freeze_today(monkeypatch)
    birthdate = date(REFERENCE_TODAY.year - 17, REFERENCE_TODAY.month, REFERENCE_TODAY.day)
    assert _is_underage(birthdate) is True


def test_is_underage_false_for_18_year_old_today(monkeypatch) -> None:
    _freeze_today(monkeypatch)
    birthdate = date(REFERENCE_TODAY.year - 18, REFERENCE_TODAY.month, REFERENCE_TODAY.day)
    assert _is_underage(birthdate) is False


def test_is_underage_false_for_18_year_old_yesterday_birthday(monkeypatch) -> None:
    _freeze_today(monkeypatch)
    turns_18 = date(REFERENCE_TODAY.year - 18, REFERENCE_TODAY.month, REFERENCE_TODAY.day)
    assert _is_underage(turns_18 - timedelta(days=1)) is False


def test_is_underage_true_for_18th_birthday_tomorrow(monkeypatch) -> None:
    _freeze_today(monkeypatch)
    turns_18 = date(REFERENCE_TODAY.year - 18, REFERENCE_TODAY.month, REFERENCE_TODAY.day)
    assert _is_underage(turns_18 + timedelta(days=1)) is True
