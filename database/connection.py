# database/connection.py

from pathlib import Path

import aiosqlite


BASE_DIR = Path(__file__).resolve().parents[1]

DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "eden.db"

from config.leveling import (
    MESSAGE_XP,
    VOICE_XP_PER_MINUTE
)

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
                xp INTEGER NOT NULL DEFAULT 0,
                currency INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        cursor = await db.execute(
            "PRAGMA table_info(member_stats)"
        )

        columns = {
            row[1]
            for row in await cursor.fetchall()
        }

        if "xp" not in columns:
            await db.execute(
                """
                ALTER TABLE member_stats
                ADD COLUMN xp INTEGER NOT NULL DEFAULT 0
                """
            )

            await db.execute(
                """
                UPDATE member_stats
                SET xp =
                    messages * ?
                    + CAST(voice_seconds / 60 AS INTEGER) * ?
                """,
                (
                    MESSAGE_XP,
                    VOICE_XP_PER_MINUTE
                )
            )

            print("[DB] Добавлена колонка xp")

        await db.commit()