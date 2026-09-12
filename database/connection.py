from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "eden.db"


@asynccontextmanager
async def get_db():
    """
    Создаёт настроенное подключение к SQLite.
    """

    DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    db = await aiosqlite.connect(
        DB_PATH,
        timeout=10,
    )

    try:
        await db.execute(
            "PRAGMA busy_timeout = 5000"
        )

        await db.execute(
            "PRAGMA foreign_keys = ON"
        )

        yield db

    finally:
        await db.close()
