import logging

from config.leveling import (
    MESSAGE_XP,
    VOICE_XP_PER_MINUTE,
)
from database.connection import get_db


logger = logging.getLogger("lost_eden.database")

SCHEMA_VERSION = 2


async def _get_columns(
    db,
    table_name: str,
) -> set[str]:
    cursor = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    rows = await cursor.fetchall()
    await cursor.close()

    return {
        str(row[1])
        for row in rows
    }


async def _create_tables(db) -> None:
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

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY AUTOINCREMENT,

            guild_id INTEGER NOT NULL,
            type TEXT NOT NULL,

            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',

            host_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',

            max_participants INTEGER,
            starts_at INTEGER,

            channel_id INTEGER,
            message_id INTEGER,

            reward_preset TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_participants (
            activity_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,

            role TEXT NOT NULL DEFAULT 'participant',
            joined_at INTEGER NOT NULL,

            PRIMARY KEY (
                activity_id,
                user_id
            ),

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_results (
            activity_id INTEGER PRIMARY KEY,

            winner_user_id INTEGER NOT NULL,
            submitted_by INTEGER NOT NULL,
            confirmed_by INTEGER,

            status TEXT NOT NULL DEFAULT 'pending',

            created_at INTEGER NOT NULL,
            confirmed_at INTEGER,

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_payouts (
            activity_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,

            reward_key TEXT NOT NULL,
            reward_kind TEXT NOT NULL,
            amount INTEGER NOT NULL,

            actor_id INTEGER,
            granted_at INTEGER NOT NULL,

            PRIMARY KEY (
                activity_id,
                user_id,
                reward_key
            ),

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_reward_decisions (
            activity_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            policy_key TEXT NOT NULL,
            status TEXT NOT NULL,
            decided_at INTEGER NOT NULL,

            PRIMARY KEY (
                activity_id,
                user_id,
                policy_key
            ),

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )

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

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS close_settings (
            activity_id INTEGER PRIMARY KEY,
            team_mode TEXT NOT NULL,
            captain_a_id INTEGER,
            captain_b_id INTEGER,
            draft_turn TEXT,

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS close_results (
            activity_id INTEGER PRIMARY KEY,
            winner_team TEXT NOT NULL,
            submitted_by INTEGER NOT NULL,
            confirmed_by INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            confirmed_at INTEGER,

            FOREIGN KEY (activity_id)
                REFERENCES activities(activity_id)
                ON DELETE CASCADE
        )
        """
    )


async def _apply_legacy_migrations(db) -> None:
    activity_columns = await _get_columns(
        db,
        "activities",
    )

    if "reward_preset" not in activity_columns:
        await db.execute(
            """
            ALTER TABLE activities
            ADD COLUMN reward_preset TEXT
            """
        )

        await db.execute(
            """
            UPDATE activities
            SET reward_preset = 'standard'
            WHERE type = 'event'
              AND status IN ('open', 'running')
            """
        )

        logger.info(
            "Добавлена колонка activities.reward_preset"
        )

    member_columns = await _get_columns(
        db,
        "member_stats",
    )

    if "eden_cases" not in member_columns:
        await db.execute(
            """
            ALTER TABLE member_stats
            ADD COLUMN eden_cases INTEGER NOT NULL DEFAULT 0
            """
        )

        logger.info(
            "Добавлена колонка member_stats.eden_cases"
        )

    if "xp" not in member_columns:
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

        logger.info(
            "Добавлена колонка member_stats.xp"
        )


async def _create_indexes(db) -> None:
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

    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_activities_guild_status
        ON activities (
            guild_id,
            status
        )
        """
    )

    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_activity_participants_activity
        ON activity_participants (
            activity_id,
            joined_at
        )
        """
    )


async def init_db() -> None:
    """
    Создаёт актуальную схему SQLite и применяет совместимые миграции.
    """

    async with get_db() as db:
        await db.execute(
            "PRAGMA journal_mode = WAL"
        )

        await db.execute(
            "PRAGMA synchronous = NORMAL"
        )

        try:
            await _create_tables(db)
            await _apply_legacy_migrations(db)
            await _create_indexes(db)

            await db.execute(
                f"PRAGMA user_version = {SCHEMA_VERSION}"
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    logger.info(
        "Схема базы данных готова, version=%s",
        SCHEMA_VERSION,
    )
