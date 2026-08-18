import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from conftest import make_test_user
from ev_twin_api.core.database import Database
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUserUpdate
from ev_twin_api.schemas.auth import AppRole
from ev_twin_api.services.admin_user_service import (
    InvitedIdentity,
    LastActiveAdminError,
    SqlAlchemyAdminUserRepository,
    UserAdministrationUnavailableError,
)
from sqlalchemy.exc import SQLAlchemyError

ADMIN = make_test_user(AppRole.ADMIN)
OTHER_ADMIN_ID = UUID("00000000-0000-0000-0000-000000000007")
TARGET_ID = UUID("00000000-0000-0000-0000-000000000008")
NOW = datetime(2026, 8, 14, 3, 0, tzinfo=UTC)


class FakeMappings:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def one_or_none(self) -> dict[str, object] | None:
        assert len(self._rows) <= 1
        return self._rows[0] if self._rows else None


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._rows)


class FakeTransaction:
    def __init__(self, session: "FakeSession") -> None:
        self._session = session

    async def __aenter__(self) -> None:
        self._session.transaction_entered += 1

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc, traceback
        self._session.transaction_commits.append(exc_type is None)


class FakeSession:
    def __init__(self, results: list[FakeResult | Exception]) -> None:
        self._results = results
        self.executions: list[tuple[str, dict[str, object]]] = []
        self.transaction_entered = 0
        self.transaction_commits: list[bool] = []

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(
        self,
        statement: object,
        params: dict[str, object] | None = None,
    ) -> FakeResult:
        self.executions.append((str(statement), params or {}))
        assert self._results, "unexpected SQL statement"
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeDatabase:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[FakeSession]:
        yield self._session


def user_row(
    *,
    user_id: UUID = TARGET_ID,
    role: AppRole = AppRole.DESIGNER,
    active: bool = True,
    email: str = "user@example.com",
) -> dict[str, object]:
    return {
        "id": user_id,
        "email": email,
        "display_name": "Factory User",
        "role": role.value,
        "is_active": active,
        "created_at": NOW,
    }


@pytest.mark.asyncio
async def test_role_and_status_audits_precede_update_in_one_transaction() -> None:
    session = FakeSession(
        [
            FakeResult([{"id": ADMIN.id}, {"id": OTHER_ADMIN_ID}]),
            FakeResult([user_row()]),
            FakeResult(),
            FakeResult(),
            FakeResult(),
        ]
    )
    repository = SqlAlchemyAdminUserRepository(cast(Database, FakeDatabase(session)))
    request_id = uuid4()

    change = await repository.update(
        TARGET_ID,
        AdminUserUpdate(role=AppRole.MONITOR, is_active=False),
        actor=ADMIN,
        request_id=request_id,
        occurred_at=NOW,
    )

    statements = [statement for statement, _ in session.executions]
    assert session.transaction_entered == 1
    assert session.transaction_commits == [True]
    assert ["INSERT INTO public.audit_events" in statement for statement in statements] == [
        False,
        False,
        True,
        True,
        False,
    ]
    assert "UPDATE public.profiles" in statements[-1]
    audit_params = [
        params for statement, params in session.executions if "audit_events" in statement
    ]
    assert [params["action"] for params in audit_params] == [
        "ROLE_CHANGED",
        "USER_DISABLED",
    ]
    assert {params["request_id"] for params in audit_params} == {request_id}
    assert change.before.is_active is True
    assert change.after.is_active is False
    assert change.after.role == AppRole.MONITOR


@pytest.mark.asyncio
async def test_final_active_admin_cannot_disable_or_demote_themselves() -> None:
    for update in (
        AdminUserUpdate(is_active=False),
        AdminUserUpdate(role=AppRole.DESIGNER),
    ):
        session = FakeSession(
            [
                FakeResult([{"id": ADMIN.id}]),
                FakeResult(
                    [
                        user_row(
                            user_id=ADMIN.id,
                            role=AppRole.ADMIN,
                            email=ADMIN.email,
                        )
                    ]
                ),
            ]
        )
        repository = SqlAlchemyAdminUserRepository(cast(Database, FakeDatabase(session)))

        with pytest.raises(LastActiveAdminError):
            await repository.update(
                ADMIN.id,
                update,
                actor=ADMIN,
                request_id=uuid4(),
                occurred_at=NOW,
            )

        assert session.transaction_commits == [False]
        assert len(session.executions) == 2


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_profile_update() -> None:
    session = FakeSession(
        [
            FakeResult([{"id": ADMIN.id}]),
            FakeResult([user_row()]),
            SQLAlchemyError("audit unavailable"),
        ]
    )
    repository = SqlAlchemyAdminUserRepository(cast(Database, FakeDatabase(session)))

    with pytest.raises(UserAdministrationUnavailableError):
        await repository.update(
            TARGET_ID,
            AdminUserUpdate(is_active=False),
            actor=ADMIN,
            request_id=uuid4(),
            occurred_at=NOW,
        )

    assert session.transaction_commits == [False]
    assert not any(
        statement.strip().startswith("UPDATE public.profiles")
        for statement, _ in session.executions
    )


@pytest.mark.asyncio
async def test_invited_profile_activation_and_audit_share_transaction_without_secrets() -> None:
    session = FakeSession(
        [
            FakeResult([user_row(active=False, email="new@example.com")]),
            FakeResult(),
            FakeResult(),
        ]
    )
    repository = SqlAlchemyAdminUserRepository(cast(Database, FakeDatabase(session)))
    invite = AdminInviteRequest(
        email="new@example.com",
        display_name="New Monitor",
        role=AppRole.MONITOR,
    )

    invited = await repository.activate_invited_user(
        InvitedIdentity(id=TARGET_ID, email=invite.email),
        invite,
        actor=ADMIN,
        request_id=uuid4(),
        occurred_at=NOW,
    )

    assert session.transaction_commits == [True]
    assert "INSERT INTO public.audit_events" in session.executions[1][0]
    assert "UPDATE public.profiles" in session.executions[2][0]
    audit_params = session.executions[1][1]
    assert audit_params["action"] == "USER_INVITED"
    serialized_audit = json.dumps(audit_params, default=str)
    assert "password" not in serialized_audit
    assert "token" not in serialized_audit
    assert invited.display_name == "New Monitor"
    assert invited.role == AppRole.MONITOR
    assert invited.is_active is True
