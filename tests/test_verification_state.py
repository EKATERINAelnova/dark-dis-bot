import pytest

from services.verification_roles import (
    get_verified_role_id,
    is_member_verified,
)


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id


class FakeMember:
    def __init__(self, role_ids: list[int]):
        self.roles = [FakeRole(role_id) for role_id in role_ids]


def test_verification_role_id_is_optional(monkeypatch):
    monkeypatch.delenv("VERIFIED_ROLE_ID", raising=False)

    assert get_verified_role_id() is None


def test_member_is_verified_by_configured_role(monkeypatch):
    monkeypatch.setenv("VERIFIED_ROLE_ID", "123")

    member = FakeMember([10, 123, 999])

    assert is_member_verified(member) is True


def test_member_without_role_is_not_verified(monkeypatch):
    monkeypatch.setenv("VERIFIED_ROLE_ID", "123")

    member = FakeMember([10, 20])

    assert is_member_verified(member) is False


def test_invalid_verification_role_id_is_rejected(monkeypatch):
    monkeypatch.setenv("VERIFIED_ROLE_ID", "not-a-role")

    with pytest.raises(RuntimeError):
        get_verified_role_id()
