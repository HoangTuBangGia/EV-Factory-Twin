import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Protocol, cast
from uuid import UUID, uuid4

from fastapi import Depends, Request
from sqlalchemy import text

from ev_twin_api.core.database import Database
from ev_twin_api.schemas.audit import AuditAction
from ev_twin_api.schemas.auth import AppRole, CurrentUser
from ev_twin_api.schemas.command import (
    ApplyScenarioRequest,
    Command,
    CommandAcknowledgementRequest,
    CommandAttempt,
    CommandResultRequest,
    CommandStatus,
    CommandType,
    EdgeCommand,
)
from ev_twin_api.schemas.scenario import ScenarioStatus
from ev_twin_api.schemas.task import CreateTransportTaskRequest
from ev_twin_api.schemas.websocket import command_updated_event
from ev_twin_api.services.audit_service import AuditRepository, PendingAuditEvent
from ev_twin_api.services.runtime_health import RuntimeHealthService
from ev_twin_api.services.scenario_service import (
    InvalidScenarioTransitionError,
    ScenarioService,
)
from ev_twin_api.services.websocket_manager import WebSocketManager

logger = logging.getLogger("ev_twin_api")


class CommandNotFoundError(LookupError):
    pass


class CommandConflictError(RuntimeError):
    pass


class CommandRepository(Protocol):
    async def create(self, command: Command) -> Command: ...
    async def get(self, operation_id: UUID) -> Command | None: ...
    async def list_all(self) -> list[Command]: ...
    async def lease(self, bridge_id: str, now: datetime) -> Command | None: ...
    async def acknowledge(
        self, request: CommandAcknowledgementRequest, now: datetime
    ) -> Command: ...
    async def result(self, request: CommandResultRequest, now: datetime) -> Command: ...
    async def retry(self, operation_id: UUID, now: datetime) -> Command: ...
    async def expire(self, now: datetime) -> list[Command]: ...


class InMemoryCommandRepository:
    def __init__(self) -> None:
        self._commands: dict[UUID, Command] = {}
        self._lock = asyncio.Lock()

    async def create(self, command: Command) -> Command:
        async with self._lock:
            if any(
                existing.command_type == command.command_type
                and (
                    existing.scenario_id == command.scenario_id
                    if command.command_type == CommandType.APPLY_SCENARIO
                    else existing.task_id == command.task_id
                )
                and existing.status in {CommandStatus.PENDING, CommandStatus.ACKNOWLEDGED}
                for existing in self._commands.values()
            ):
                raise CommandConflictError("command target already has an active command")
            self._commands[command.operation_id] = command
            return command.model_copy(deep=True)

    async def get(self, operation_id: UUID) -> Command | None:
        async with self._lock:
            value = self._commands.get(operation_id)
            return value.model_copy(deep=True) if value else None

    async def list_all(self) -> list[Command]:
        async with self._lock:
            return [item.model_copy(deep=True) for item in self._commands.values()]

    async def lease(self, bridge_id: str, now: datetime) -> Command | None:
        async with self._lock:
            for command in self._commands.values():
                attempt = command.attempts[-1]
                if command.status == CommandStatus.PENDING and attempt.leased_by is None:
                    expires = now + timedelta(seconds=command.timeout_seconds)
                    attempt.leased_by = bridge_id
                    attempt.lease_expires_at = expires
                    command.updated_at = now
                    return command.model_copy(deep=True)
            return None

    async def acknowledge(self, request: CommandAcknowledgementRequest, now: datetime) -> Command:
        async with self._lock:
            command, attempt = self._attempt(request.operation_id, request.attempt_number)
            if attempt.leased_by != request.bridge_id:
                raise CommandConflictError("command attempt is leased by another bridge")
            if command.status == CommandStatus.ACKNOWLEDGED:
                return command.model_copy(deep=True)
            self._ensure_live(attempt, now)
            command.status = attempt.status = CommandStatus.ACKNOWLEDGED
            attempt.acknowledged_at = now
            command.updated_at = now
            return command.model_copy(deep=True)

    async def result(self, request: CommandResultRequest, now: datetime) -> Command:
        if request.status not in {
            CommandStatus.COMPLETED,
            CommandStatus.REQUIRES_RELAUNCH,
            CommandStatus.FAILED,
        }:
            raise CommandConflictError(
                "result status must be COMPLETED, REQUIRES_RELAUNCH or FAILED"
            )
        async with self._lock:
            command, attempt = self._attempt(request.operation_id, request.attempt_number)
            if attempt.leased_by != request.bridge_id:
                raise CommandConflictError("command attempt is leased by another bridge")
            if command.status == request.status:
                return command.model_copy(deep=True)
            self._ensure_live(attempt, now)
            if command.status != CommandStatus.ACKNOWLEDGED:
                raise CommandConflictError("command must be acknowledged before result")
            command.status = attempt.status = request.status
            attempt.completed_at = now
            attempt.detail = request.detail
            command.updated_at = now
            return command.model_copy(deep=True)

    async def retry(self, operation_id: UUID, now: datetime) -> Command:
        async with self._lock:
            command = self._commands.get(operation_id)
            if command is None:
                raise CommandNotFoundError(f"Command '{operation_id}' not found")
            self._expire(command, now)
            if command.status not in {
                CommandStatus.REQUIRES_RELAUNCH,
                CommandStatus.FAILED,
                CommandStatus.TIMED_OUT,
            }:
                raise CommandConflictError(
                    "only relaunch-required, failed or timed-out commands can retry"
                )
            if len(command.attempts) > command.max_retries:
                raise CommandConflictError("command retry budget exhausted")
            command.attempts.append(
                CommandAttempt(
                    attempt_number=len(command.attempts) + 1,
                    status=CommandStatus.PENDING,
                )
            )
            command.status = CommandStatus.PENDING
            command.updated_at = now
            return command.model_copy(deep=True)

    async def expire(self, now: datetime) -> list[Command]:
        async with self._lock:
            expired: list[Command] = []
            for command in self._commands.values():
                before = command.status
                self._expire(command, now)
                if before != command.status:
                    expired.append(command.model_copy(deep=True))
            return expired

    def _attempt(self, operation_id: UUID, number: int) -> tuple[Command, CommandAttempt]:
        command = self._commands.get(operation_id)
        if command is None:
            raise CommandNotFoundError(f"Command '{operation_id}' not found")
        attempt = next((item for item in command.attempts if item.attempt_number == number), None)
        if attempt is None:
            raise CommandNotFoundError(f"Command attempt '{operation_id}/{number}' not found")
        return command, attempt

    def _ensure_live(self, attempt: CommandAttempt, now: datetime) -> None:
        if attempt.lease_expires_at is None or attempt.lease_expires_at <= now:
            attempt.status = CommandStatus.TIMED_OUT
            raise CommandConflictError("command attempt timed out")

    def _expire(self, command: Command, now: datetime) -> None:
        attempt = command.attempts[-1]
        deadline = attempt.lease_expires_at or (
            command.updated_at + timedelta(seconds=command.timeout_seconds)
        )
        if (
            command.status in {CommandStatus.PENDING, CommandStatus.ACKNOWLEDGED}
            and deadline <= now
        ):
            command.status = attempt.status = CommandStatus.TIMED_OUT
            attempt.completed_at = now
            attempt.detail = "command attempt timed out"
            command.updated_at = now


class SqlAlchemyCommandRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, command: Command) -> Command:
        async with self._database.session() as session, session.begin():
            try:
                await session.execute(
                    text("""
                        insert into public.commands (
                            operation_id, command_type, scenario_id, task_id, status, payload,
                            timeout_seconds, max_retries, requested_by, created_at, updated_at
                        ) values (
                            :operation_id, cast(:command_type as public.command_type),
                            :scenario_id, :task_id, 'PENDING', cast(:payload as jsonb),
                            :timeout_seconds, :max_retries, :requested_by, :created_at, :updated_at
                        )
                    """),
                    {
                        "operation_id": command.operation_id,
                        "command_type": command.command_type.value,
                        "scenario_id": command.scenario_id,
                        "task_id": command.task_id,
                        "payload": command.payload.model_dump_json(),
                        "timeout_seconds": command.timeout_seconds,
                        "max_retries": command.max_retries,
                        "requested_by": command.requested_by,
                        "created_at": command.created_at,
                        "updated_at": command.updated_at,
                    },
                )
                await session.execute(
                    text("""
                        insert into public.command_attempts
                            (operation_id, attempt_number, status)
                        values (:operation_id, 1, 'PENDING')
                    """),
                    {"operation_id": command.operation_id},
                )
            except Exception as error:
                raise CommandConflictError(
                    "command target already has an active command"
                ) from error
        return command

    async def get(self, operation_id: UUID) -> Command | None:
        async with self._database.session() as session:
            return await self._load(session, operation_id)

    async def list_all(self) -> list[Command]:
        async with self._database.session() as session:
            result = await session.execute(
                text("select operation_id from public.commands order by created_at, operation_id")
            )
            identifiers = list(result.scalars())
            return [command for item in identifiers if (command := await self._load(session, item))]

    async def lease(self, bridge_id: str, now: datetime) -> Command | None:
        async with self._database.session() as session, session.begin():
            await self._expire(session, now)
            result = await session.execute(
                text("""
                    select a.operation_id, a.attempt_number, c.timeout_seconds
                    from public.command_attempts a
                    join public.commands c using (operation_id)
                    where c.status = 'PENDING' and a.status = 'PENDING' and a.leased_by is null
                    order by c.created_at, a.attempt_number
                    for update of a skip locked limit 1
                """)
            )
            row = result.mappings().one_or_none()
            if row is None:
                return None
            expires = now + timedelta(seconds=float(row["timeout_seconds"]))
            await session.execute(
                text("""
                    update public.command_attempts
                    set leased_by=:bridge_id, leased_at=:now, lease_expires_at=:expires
                    where operation_id=:operation_id and attempt_number=:attempt_number
                """),
                {**row, "bridge_id": bridge_id, "now": now, "expires": expires},
            )
            return await self._load(session, row["operation_id"])

    async def acknowledge(self, request: CommandAcknowledgementRequest, now: datetime) -> Command:
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    update public.command_attempts set status='ACKNOWLEDGED', acknowledged_at=:now
                    where operation_id=:operation_id and attempt_number=:attempt_number
                      and leased_by=:bridge_id and status='PENDING' and lease_expires_at > :now
                    returning operation_id
                """),
                {**request.model_dump(), "now": now},
            )
            if result.scalar_one_or_none() is None:
                existing = await self._load(session, request.operation_id)
                if existing and existing.status == CommandStatus.ACKNOWLEDGED:
                    return existing
                raise CommandConflictError("command acknowledgement is stale or invalid")
            await session.execute(
                text("""
                    update public.commands set status='ACKNOWLEDGED', updated_at=:now
                    where operation_id=:id
                """),
                {"id": request.operation_id, "now": now},
            )
            await self._ack_event(session, request, CommandStatus.ACKNOWLEDGED, "", now)
            command = await self._load(session, request.operation_id)
            assert command is not None
            return command

    async def result(self, request: CommandResultRequest, now: datetime) -> Command:
        if request.status not in {
            CommandStatus.COMPLETED,
            CommandStatus.REQUIRES_RELAUNCH,
            CommandStatus.FAILED,
        }:
            raise CommandConflictError(
                "result status must be COMPLETED, REQUIRES_RELAUNCH or FAILED"
            )
        async with self._database.session() as session, session.begin():
            result = await session.execute(
                text("""
                    update public.command_attempts
                    set status=cast(:status as public.command_status),
                        completed_at=:now, detail=:detail
                    where operation_id=:operation_id and attempt_number=:attempt_number
                      and leased_by=:bridge_id and status='ACKNOWLEDGED' and lease_expires_at > :now
                    returning operation_id
                """),
                {**request.model_dump(mode="json"), "now": now},
            )
            if result.scalar_one_or_none() is None:
                existing = await self._load(session, request.operation_id)
                if existing and existing.status == request.status:
                    return existing
                raise CommandConflictError("command result is stale or invalid")
            await session.execute(
                text("""
                    update public.commands
                    set status=cast(:status as public.command_status), updated_at=:now
                    where operation_id=:operation_id
                """),
                {**request.model_dump(mode="json"), "now": now},
            )
            await self._ack_event(session, request, request.status, request.detail, now)
            command = await self._load(session, request.operation_id)
            assert command is not None
            return command

    async def retry(self, operation_id: UUID, now: datetime) -> Command:
        async with self._database.session() as session, session.begin():
            await self._expire(session, now)
            command = await self._load(session, operation_id)
            if command is None:
                raise CommandNotFoundError(f"Command '{operation_id}' not found")
            if command.status not in {
                CommandStatus.REQUIRES_RELAUNCH,
                CommandStatus.FAILED,
                CommandStatus.TIMED_OUT,
            }:
                raise CommandConflictError(
                    "only relaunch-required, failed or timed-out commands can retry"
                )
            if len(command.attempts) > command.max_retries:
                raise CommandConflictError("command retry budget exhausted")
            number = len(command.attempts) + 1
            await session.execute(
                text("""
                    insert into public.command_attempts (operation_id, attempt_number, status)
                    values (:operation_id, :number, 'PENDING')
                """),
                {"operation_id": operation_id, "number": number},
            )
            await session.execute(
                text("""
                    update public.commands set status='PENDING', updated_at=:now
                    where operation_id=:id
                """),
                {"id": operation_id, "now": now},
            )
            updated = await self._load(session, operation_id)
            assert updated is not None
            return updated

    async def expire(self, now: datetime) -> list[Command]:
        async with self._database.session() as session, session.begin():
            identifiers = await self._expire(session, now)
            return [
                command
                for identifier in identifiers
                if (command := await self._load(session, identifier)) is not None
            ]

    async def _expire(self, session, now: datetime) -> list[UUID]:
        result = await session.execute(
            text("""
                with expired as (
                    update public.command_attempts
                    set status='TIMED_OUT', completed_at=:now, detail='command attempt timed out'
                    from public.commands c
                    where command_attempts.operation_id = c.operation_id
                      and command_attempts.status in ('PENDING','ACKNOWLEDGED')
                      and (
                        command_attempts.lease_expires_at <= :now
                        or (
                          command_attempts.lease_expires_at is null
                          and c.updated_at + c.timeout_seconds * interval '1 second' <= :now
                        )
                      )
                    returning command_attempts.operation_id
                )
                update public.commands set status='TIMED_OUT', updated_at=:now
                where operation_id in (select operation_id from expired)
                returning operation_id
            """),
            {"now": now},
        )
        return list(result.scalars())

    async def _load(self, session, operation_id: UUID) -> Command | None:
        result = await session.execute(
            text("select * from public.commands where operation_id=:id"), {"id": operation_id}
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        attempts_result = await session.execute(
            text("""
                select attempt_number, status::text status, leased_by, lease_expires_at,
                       acknowledged_at, completed_at, detail
                from public.command_attempts where operation_id=:id order by attempt_number
            """),
            {"id": operation_id},
        )
        return Command(
            operation_id=row["operation_id"],
            command_type=CommandType(str(row["command_type"])),
            scenario_id=row["scenario_id"],
            task_id=row["task_id"],
            status=CommandStatus(str(row["status"])),
            payload=row["payload"],
            timeout_seconds=row["timeout_seconds"],
            max_retries=row["max_retries"],
            attempts=[CommandAttempt.model_validate(item) for item in attempts_result.mappings()],
            requested_by=row["requested_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def _ack_event(self, session, request, status, detail: str, now: datetime) -> None:
        await session.execute(
            text("""
                insert into public.command_acknowledgements
                    (operation_id, attempt_number, status, bridge_id, detail, created_at)
                values (:operation_id, :attempt_number, cast(:status as public.command_status),
                        :bridge_id, :detail, :now)
                on conflict (operation_id, attempt_number, status) do nothing
            """),
            {
                **request.model_dump(mode="json"),
                "status": status.value,
                "detail": detail,
                "now": now,
            },
        )


class CommandService:
    def __init__(
        self,
        repository: CommandRepository,
        scenarios: ScenarioService,
        websocket_manager: WebSocketManager,
        audit_repository: AuditRepository,
        runtime_health: RuntimeHealthService | None = None,
        *,
        sweep_seconds: float = 1.0,
    ) -> None:
        self._repository = repository
        self._scenarios = scenarios
        self._websockets = websocket_manager
        self._audit_repository = audit_repository
        self._runtime_health = runtime_health
        self._sweep_seconds = sweep_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="command-timeout-sweep")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self._expire_commands()
            except Exception:
                logger.exception("command timeout sweep failed; retrying next cadence")
            await asyncio.sleep(self._sweep_seconds)

    async def apply(
        self, scenario_id: str, request: ApplyScenarioRequest, actor: CurrentUser
    ) -> Command:
        scenario = await self._scenarios.get(scenario_id)
        if scenario.status != ScenarioStatus.APPROVED:
            raise InvalidScenarioTransitionError(
                f"Scenario '{scenario_id}' must be APPROVED before apply; "
                f"current status is {scenario.status}"
            )
        if scenario.created_by == actor.id:
            raise InvalidScenarioTransitionError("scenario creator cannot apply their own scenario")
        now = datetime.now(UTC)
        command = await self._repository.create(
            Command(
                operation_id=uuid4(),
                command_type=CommandType.APPLY_SCENARIO,
                scenario_id=scenario.id,
                status=CommandStatus.PENDING,
                payload=scenario.config,
                timeout_seconds=request.timeout_seconds,
                max_retries=request.max_retries,
                attempts=[CommandAttempt(attempt_number=1, status=CommandStatus.PENDING)],
                requested_by=actor.id,
                created_at=now,
                updated_at=now,
            )
        )
        await self._audit(command, AuditAction.COMMAND_CREATED)
        await self._broadcast(command)
        return command

    async def create_transport_task(
        self, request: CreateTransportTaskRequest, actor: CurrentUser
    ) -> Command:
        now = datetime.now(UTC)
        command = await self._repository.create(
            Command(
                operation_id=uuid4(),
                command_type=CommandType.CREATE_TRANSPORT_TASK,
                task_id=request.task_id,
                status=CommandStatus.PENDING,
                payload=request,
                timeout_seconds=30.0,
                max_retries=1,
                attempts=[CommandAttempt(attempt_number=1, status=CommandStatus.PENDING)],
                requested_by=actor.id,
                created_at=now,
                updated_at=now,
            )
        )
        await self._audit(command, AuditAction.COMMAND_CREATED)
        await self._broadcast(command)
        return command

    async def list(self) -> list[Command]:
        await self._expire_commands()
        return await self._repository.list_all()

    async def get(self, operation_id: UUID) -> Command:
        await self._expire_commands()
        command = await self._repository.get(operation_id)
        if command is None:
            raise CommandNotFoundError(f"Command '{operation_id}' not found")
        return command

    async def lease(self, bridge_id: str) -> EdgeCommand | None:
        await self._expire_commands()
        command = await self._repository.lease(bridge_id, datetime.now(UTC))
        if command is None:
            return None
        attempt = command.attempts[-1]
        return EdgeCommand(
            operation_id=command.operation_id,
            attempt_number=attempt.attempt_number,
            command_type=command.command_type,
            scenario_id=command.scenario_id,
            task_id=command.task_id,
            payload=command.payload,
            timeout_seconds=command.timeout_seconds,
        )

    async def acknowledge(self, request: CommandAcknowledgementRequest) -> Command:
        command = await self._repository.acknowledge(request, datetime.now(UTC))
        await self._audit(command, AuditAction.COMMAND_ACKNOWLEDGED)
        await self._broadcast(command)
        return command

    async def result(self, request: CommandResultRequest) -> Command:
        command = await self._repository.result(request, datetime.now(UTC))
        if (
            command.status == CommandStatus.COMPLETED
            and command.command_type == CommandType.APPLY_SCENARIO
        ):
            assert command.scenario_id is not None
            actor = CurrentUser(
                id=command.requested_by,
                email="edge-command@internal.invalid",
                display_name="Command requester",
                role=AppRole.MONITOR,
                is_active=True,
            )
            scenario = await self._scenarios.get(command.scenario_id)
            if scenario.status == ScenarioStatus.APPROVED:
                await self._scenarios.complete_apply(command.scenario_id, actor)
            elif scenario.status != ScenarioStatus.APPLIED:
                raise CommandConflictError(
                    f"completed command cannot apply scenario from {scenario.status}"
                )
        await self._audit(
            command,
            AuditAction.COMMAND_COMPLETED
            if command.status == CommandStatus.COMPLETED
            else AuditAction.COMMAND_FAILED,
        )
        await self._broadcast(command)
        return command

    async def retry(self, operation_id: UUID) -> Command:
        await self._expire_commands()
        command = await self._repository.retry(operation_id, datetime.now(UTC))
        if self._runtime_health is not None:
            await self._runtime_health.note_command_timeout(operation_id, False)
        await self._audit(command, AuditAction.COMMAND_RETRIED)
        await self._broadcast(command)
        return command

    async def _broadcast(self, command: Command) -> None:
        await self._websockets.broadcast(command_updated_event(command))

    async def _expire_commands(self) -> None:
        for command in await self._repository.expire(datetime.now(UTC)):
            if self._runtime_health is not None:
                await self._runtime_health.note_command_timeout(command.operation_id, True)
            await self._audit(command, AuditAction.COMMAND_TIMED_OUT)
            await self._broadcast(command)

    async def _audit(self, command: Command, action: AuditAction) -> None:
        await self._audit_repository.record(
            PendingAuditEvent(
                actor_id=command.requested_by,
                actor_role=AppRole.MONITOR,
                action=action,
                resource_type="command",
                resource_id=str(command.operation_id),
                before_data=None,
                after_data=command.model_dump(mode="json"),
                request_id=command.operation_id,
                created_at=datetime.now(UTC),
            )
        )


def get_command_service(request: Request) -> CommandService:
    return cast(CommandService, request.app.state.command_service)


CommandServiceDep = Annotated[CommandService, Depends(get_command_service)]
