from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from config.leveling import (
    MESSAGE_XP,
    VOICE_XP_PER_MINUTE,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "eden.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

@asynccontextmanager
async def get_db():
    """
    Создаёт настроенное подключение к SQLite.

    Все модули проекта постепенно
    переведём на использование этой функции.
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
        # SQLite будет ждать освобождения БД,
        # вместо мгновенного "database is locked".
        await db.execute(
            "PRAGMA busy_timeout = 5000"
        )

        # Включаем поддержку foreign keys.
        # Пока они почти не используются,
        # но база готова к ним заранее.
        await db.execute(
            "PRAGMA foreign_keys = ON"
        )

        yield db

    finally:
        await db.close()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

async def init_db() -> None:
    """
    Создаёт и обновляет структуру базы данных.
    """

    DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with get_db() as db:

        # =====================================================
        # SQLITE SETTINGS
        # =====================================================

        # WAL позволяет чтению и записи
        # меньше мешать друг другу.
        await db.execute(
            "PRAGMA journal_mode = WAL"
        )

        # Хороший баланс между
        # надёжностью и производительностью.
        await db.execute(
            "PRAGMA synchronous = NORMAL"
        )

        # =====================================================
        # MEMBER STATS
        # =====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS member_stats (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                messages INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                currency INTEGER NOT NULL DEFAULT 0,
                eden_cases INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS achievement_unlocks (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                achievement_key TEXT NOT NULL,
                unlocked_at INTEGER NOT NULL,

                PRIMARY KEY (
                    guild_id,
                    user_id,
                    achievement_key
                )
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_rituals (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                last_ritual_at INTEGER NOT NULL DEFAULT 0,

                PRIMARY KEY (
                    guild_id,
                    user_id
                )
            )
            """
        )

        # =====================================================
        # MIGRATION: XP
        # =====================================================

        cursor = await db.execute(
            "PRAGMA table_info(member_stats)"
        )

        columns = {
            row[1]
            for row in await cursor.fetchall()
        }

        await cursor.close()

        if "eden_cases" not in columns:
            await db.execute(
                """
                ALTER TABLE member_stats
                ADD COLUMN eden_cases INTEGER NOT NULL DEFAULT 0
                """
            )

            print("[DB] Добавлена колонка eden_cases")

        # Поддержка старой базы,
        # созданной до появления XP.
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
                    + CAST(
                        voice_seconds / 60
                        AS INTEGER
                    ) * ?
                """,
                (
                    MESSAGE_XP,
                    VOICE_XP_PER_MINUTE,
                ),
            )

            print(
                "[DB] Добавлена колонка xp"
            )

        # =====================================================
        # CURRENCY TRANSACTIONS
        # =====================================================

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS currency_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,

                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,

                description TEXT,
                actor_id INTEGER,

                created_at INTEGER NOT NULL
            )
            """
        )

        # =====================================================
        # INDEXES
        # =====================================================

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_currency_transactions_user
            ON currency_transactions (
                guild_id,
                user_id,
                created_at
            )
            """
        )

        await db.commit()