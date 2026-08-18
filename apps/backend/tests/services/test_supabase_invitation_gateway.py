import json
from typing import Any
from urllib.error import HTTPError
from uuid import UUID

import pytest
from ev_twin_api.services import admin_user_service
from ev_twin_api.services.admin_user_service import (
    AdminUserConflictError,
    SupabaseUserInvitationGateway,
)
from pydantic import SecretStr

INVITED_ID = UUID("00000000-0000-0000-0000-000000000008")


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_invitation_uses_server_headers_and_never_sends_password_or_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"id": str(INVITED_ID), "email": "new@example.com"})

    monkeypatch.setattr(admin_user_service, "urlopen", fake_urlopen)
    gateway = SupabaseUserInvitationGateway(
        supabase_url="https://project.supabase.co",
        service_role_key=SecretStr("server-secret"),
    )

    identity = gateway._invite_sync(email="new@example.com", display_name="New User")

    request = captured["request"]
    payload = json.loads(request.data)  # type: ignore[attr-defined]
    assert request.full_url == "https://project.supabase.co/auth/v1/invite"  # type: ignore[attr-defined]
    assert request.headers["Authorization"] == "Bearer server-secret"  # type: ignore[attr-defined]
    assert request.headers["Apikey"] == "server-secret"  # type: ignore[attr-defined]
    assert payload == {
        "email": "new@example.com",
        "data": {"display_name": "New User"},
    }
    assert "password" not in payload
    assert "role" not in payload
    assert identity.id == INVITED_ID


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "http://remote.example.com",
        "https://user:password@example.com",
        "https://example.com?key=value",
    ],
)
def test_invitation_gateway_rejects_unsafe_project_urls(url: str) -> None:
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        SupabaseUserInvitationGateway(
            supabase_url=url,
            service_role_key=SecretStr("server-secret"),
        )


def test_duplicate_invite_is_a_safe_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> FakeResponse:
        raise HTTPError("https://project.supabase.co", 422, "duplicate", None, None)

    monkeypatch.setattr(admin_user_service, "urlopen", fail)
    gateway = SupabaseUserInvitationGateway(
        supabase_url="https://project.supabase.co",
        service_role_key=SecretStr("server-secret"),
    )

    with pytest.raises(AdminUserConflictError, match="could not invite"):
        gateway._invite_sync(email="existing@example.com", display_name="Existing")
