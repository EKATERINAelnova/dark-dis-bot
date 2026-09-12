import pytest

import services.cases as cases
from database.connection import get_db
from database.member_stats import get_member_stats


@pytest.mark.asyncio
async def test_case_xp_level_up_grants_bonus_case(
    test_db,
    monkeypatch,
):
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO member_stats (
                guild_id,
                user_id,
                xp,
                eden_cases
            )
            VALUES (?, ?, ?, ?)
            """,
            (500, 30, 90, 1),
        )
        await db.commit()

    reward = cases.CaseReward(
        kind="xp",
        amount=150,
        weight=1,
        title="150 XP",
        rarity="TEST",
    )

    monkeypatch.setattr(
        cases,
        "roll_case_reward",
        lambda: reward,
    )

    result = await cases.open_eden_case(
        guild_id=500,
        user_id=30,
    )

    stats = await get_member_stats(
        guild_id=500,
        user_id=30,
    )

    assert result is not None
    assert result.new_xp == 240
    assert result.new_level == 2
    assert result.bonus_cases == 1
    assert result.cases_left == 1

    assert stats.xp == 240
    assert stats.eden_cases == 1
