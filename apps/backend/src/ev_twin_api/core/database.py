from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseNotConfiguredError(RuntimeError):
    pass


def normalize_async_database_url(database_url: str) -> URL:
    """Return a PostgreSQL URL suitable for SQLAlchemy's asyncpg dialect."""

    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg")
    if url.drivername != "postgresql+asyncpg":
        raise ValueError("DATABASE_URL must use PostgreSQL with the asyncpg driver")
    return url


class Database:
    """Owns the optional application engine and async session factory.

    Engine creation is lazy with respect to network I/O. This lets health and
    local tests start without a database, while authenticated requests fail
    closed when no profile database has been configured.
    """

    def __init__(
        self,
        database_url: str | None,
        *,
        ssl_mode: str = "require",
    ) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        if database_url is None:
            return

        url = normalize_async_database_url(database_url)
        connect_args: dict[str, object] = {}
        if ssl_mode != "disable":
            connect_args["ssl"] = ssl_mode

        self._engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=0,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def configured(self) -> bool:
        return self._session_factory is not None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_factory is None:
            raise DatabaseNotConfiguredError("application database is not configured")
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
