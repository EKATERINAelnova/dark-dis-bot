import pytest_asyncio

import database.connection as connection
from database.schema import init_db


@pytest_asyncio.fixture
async def test_db(
    tmp_path,
    monkeypatch,
):
    """
    Каждый тест получает отдельную SQLite-базу.

    Продакшен-файл data/eden.db не используется.
    """

    db_path = tmp_path / "eden-test.db"

    monkeypatch.setattr(
        connection,
        "DB_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        connection,
        "DB_PATH",
        db_path,
    )

    await init_db()

    yield db_path
