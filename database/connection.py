# database/connection.py

from pathlib import Path

import aiosqlite


BASE_DIR = Path(__file__).resolve().parents[1]

DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "eden.db"


async def init_db() -> None:
    DB_DIR.mkdir(exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS member_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                messages INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                currency INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        await db.commit()