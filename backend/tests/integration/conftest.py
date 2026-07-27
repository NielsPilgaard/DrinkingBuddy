import asyncio
import socket

import pytest
import pytest_asyncio
import uvicorn
from httpx2 import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.db import Base, get_db
from app.main import app
from app.redis import get_redis


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:8-alpine") as rc:
        yield rc


@pytest_asyncio.fixture()
async def redis_conn(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis = Redis.from_url(f"redis://{host}:{port}/0", decode_responses=True)
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )


@pytest_asyncio.fixture()
async def db_session(db_url):
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_session, redis_conn):
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def ws_client(db_url, redis_container):
    """Async client for websocket tests.

    httpx2's `.websocket()` performs a real HTTP upgrade handshake and does not
    support ASGITransport (no websocket ASGI scope), so this runs the app on a
    real uvicorn server bound to localhost instead of using an in-process
    transport. Two concurrently-open matching connections each hold their own
    db/redis handle for the connection lifetime, so unlike `client`, db/redis
    must be created fresh per-connection rather than shared.
    """
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{host}:{port}/0"

    flush_conn = Redis.from_url(redis_url, decode_responses=True)
    await flush_conn.flushdb()
    await flush_conn.aclose()

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_redis():
        redis = Redis.from_url(redis_url, decode_responses=True)
        try:
            yield redis
        finally:
            await redis.aclose()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    server_port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=server_port, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)

    async with AsyncClient(base_url=f"http://127.0.0.1:{server_port}") as ac:
        yield ac

    server.should_exit = True
    await server_task
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
