import pytest

from database.member_stats import (
    add_voice_seconds,
    get_member_stats,
)


@pytest.mark.asyncio
async def test_voice_xp_only_for_completed_minutes(test_db):
    xp_gain, cases_gained, level = await add_voice_seconds(
        guild_id=400,
        user_id=20,
        seconds=59,
    )

    assert xp_gain == 0
    assert cases_gained == 0
    assert level == 1

    xp_gain, cases_gained, level = await add_voice_seconds(
        guild_id=400,
        user_id=20,
        seconds=1,
    )

    stats = await get_member_stats(
        guild_id=400,
        user_id=20,
    )

    assert xp_gain == 10
    assert cases_gained == 0
    assert level == 1
    assert stats.voice_seconds == 60
    assert stats.xp == 10
