import pytest

from database.member_stats import get_member_stats
from services.activities import (
    change_activity_status,
    create_activity,
    join_activity,
)
from services.activity_rewards import grant_activity_reward


@pytest.mark.asyncio
async def test_xp_reward_is_idempotent(test_db):
    activity = await create_activity(
        guild_id=300,
        activity_type="event",
        title="Reward test",
        description="",
        host_id=999,
        max_participants=10,
    )

    joined = await join_activity(
        guild_id=300,
        activity_id=activity.activity_id,
        user_id=10,
    )
    assert joined == "joined"

    status, _ = await change_activity_status(
        guild_id=300,
        activity_id=activity.activity_id,
        new_status="running",
    )
    assert status == "changed"

    status, _ = await change_activity_status(
        guild_id=300,
        activity_id=activity.activity_id,
        new_status="finished",
    )
    assert status == "changed"

    first = await grant_activity_reward(
        guild_id=300,
        activity_id=activity.activity_id,
        user_id=10,
        reward_key="test:xp",
        reward_kind="xp",
        amount=250,
    )

    second = await grant_activity_reward(
        guild_id=300,
        activity_id=activity.activity_id,
        user_id=10,
        reward_key="test:xp",
        reward_kind="xp",
        amount=250,
    )

    stats = await get_member_stats(
        guild_id=300,
        user_id=10,
    )

    assert first.status == "granted"
    assert first.new_level == 2
    assert first.cases_gained == 1

    assert second.status == "already_granted"
    assert stats.xp == 250
    assert stats.eden_cases == 1
