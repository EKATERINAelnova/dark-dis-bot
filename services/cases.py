import secrets
import time

from dataclasses import dataclass

from database.connection import get_db
from utils.leveling import level_from_xp
from config.economy import REASON_CASE


# =========================================================
# REWARDS
# =========================================================

@dataclass(frozen=True)
class CaseReward:
    kind: str
    amount: int
    weight: int

    title: str
    rarity: str


CASE_REWARDS = [
    CaseReward(
        kind="seeds",
        amount=15,
        weight=40,
        title="15 Seeds",
        rarity="COMMON",
    ),

    CaseReward(
        kind="seeds",
        amount=35,
        weight=25,
        title="35 Seeds",
        rarity="UNCOMMON",
    ),

    CaseReward(
        kind="xp",
        amount=75,
        weight=18,
        title="75 XP",
        rarity="RARE",
    ),

    CaseReward(
        kind="seeds",
        amount=100,
        weight=10,
        title="100 Seeds",
        rarity="RARE",
    ),

    CaseReward(
        kind="xp",
        amount=150,
        weight=5,
        title="150 XP",
        rarity="EPIC",
    ),

    CaseReward(
        kind="bloom",
        amount=1,
        weight=2,
        title="1 Bloom",
        rarity="EDEN",
    ),
]


randomizer = secrets.SystemRandom()


# =========================================================
# RESULT
# =========================================================

@dataclass
class CaseOpenResult:
    reward: CaseReward

    cases_left: int

    new_xp: int
    new_level: int

    new_balance: int
    blooms: int

    bonus_cases: int = 0


# =========================================================
# RANDOM REWARD
# =========================================================

def roll_case_reward() -> CaseReward:
    return randomizer.choices(
        CASE_REWARDS,
        weights=[
            reward.weight
            for reward in CASE_REWARDS
        ],
        k=1,
    )[0]


# =========================================================
# OPEN CASE
# =========================================================

async def open_eden_case(
    guild_id: int,
    user_id: int,
) -> CaseOpenResult | None:

    reward = roll_case_reward()

    async with get_db() as db:
        try:
            await db.execute(
                "BEGIN IMMEDIATE"
            )

            # =============================================
            # MEMBER
            # =============================================

            await db.execute(
                """
                INSERT OR IGNORE INTO member_stats (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            cursor = await db.execute(
                """
                SELECT
                    eden_cases,
                    xp,
                    currency,
                    blooms
                FROM member_stats
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    guild_id,
                    user_id,
                ),
            )

            row = await cursor.fetchone()
            await cursor.close()

            if row is None:
                raise RuntimeError(
                    "Не удалось получить данные участника"
                )

            eden_cases = int(row[0])
            old_xp = int(row[1])
            currency = int(row[2])
            blooms = int(row[3])

            # =============================================
            # NO CASES
            # =============================================

            if eden_cases <= 0:
                await db.rollback()

                return None

            cases_left = eden_cases - 1

            new_xp = old_xp
            new_balance = currency
            new_blooms = blooms

            bonus_cases = 0

            # =============================================
            # SEEDS
            # =============================================

            if reward.kind == "seeds":
                new_balance += reward.amount

                await db.execute(
                    """
                    INSERT INTO currency_transactions (
                        guild_id,
                        user_id,
                        amount,
                        reason,
                        description,
                        actor_id,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        guild_id,
                        user_id,
                        reward.amount,
                        REASON_CASE,
                        "eden_case",
                        None,
                        int(time.time()),
                    ),
                )

            # =============================================
            # XP
            # =============================================

            elif reward.kind == "xp":
                old_level = level_from_xp(
                    old_xp
                )

                new_xp = (
                    old_xp
                    + reward.amount
                )

                new_level = level_from_xp(
                    new_xp
                )

                bonus_cases = max(
                    0,
                    new_level - old_level,
                )

                cases_left += bonus_cases

            # =============================================
            # BLOOM
            # =============================================

            elif reward.kind == "bloom":
                new_blooms += reward.amount

            else:
                raise RuntimeError(
                    f"Неизвестная награда кейса: "
                    f"{reward.kind}"
                )

            # =============================================
            # SAVE
            # =============================================

            await db.execute(
                """
                UPDATE member_stats
                SET
                    eden_cases = ?,
                    xp = ?,
                    currency = ?,
                    blooms = ?
                WHERE guild_id = ?
                  AND user_id = ?
                """,
                (
                    cases_left,
                    new_xp,
                    new_balance,
                    new_blooms,
                    guild_id,
                    user_id,
                ),
            )

            await db.commit()

            return CaseOpenResult(
                reward=reward,
                cases_left=cases_left,

                new_xp=new_xp,
                new_level=level_from_xp(
                    new_xp
                ),

                new_balance=new_balance,
                blooms=new_blooms,

                bonus_cases=bonus_cases,
            )

        except Exception:
            await db.rollback()
            raise