import pytest

from services.activities import create_activity, get_activity, join_activity
from services.close_teams import (
    TEAM_MODE_CAPTAINS,
    TEAM_MODE_RANDOM,
    create_close_settings,
    get_close_teams,
)
from services.closes import start_close


async def create_full_close(guild_id: int, team_mode: str):
    activity = await create_activity(
        guild_id=guild_id,
        activity_type="close",
        title="Test CLOSE",
        description="",
        host_id=999,
        max_participants=4,
    )

    await create_close_settings(
        activity_id=activity.activity_id,
        team_mode=team_mode,
    )

    for user_id in (1, 2, 3, 4):
        status = await join_activity(
            guild_id=guild_id,
            activity_id=activity.activity_id,
            user_id=user_id,
        )
        assert status == "joined"

    return activity


@pytest.mark.asyncio
async def test_random_close_cannot_start_twice(test_db):
    activity = await create_full_close(
        guild_id=100,
        team_mode=TEAM_MODE_RANDOM,
    )

    first = await start_close(
        guild_id=100,
        activity_id=activity.activity_id,
    )
    second = await start_close(
        guild_id=100,
        activity_id=activity.activity_id,
    )

    assert first.status == "started"
    assert second.status == "not_open"

    stored = await get_activity(
        guild_id=100,
        activity_id=activity.activity_id,
    )
    teams = await get_close_teams(activity.activity_id)

    assert stored is not None
    assert stored.status == "running"
    assert len(teams.team_a) == 2
    assert len(teams.team_b) == 2
    assert teams.waiting == []
    assert set(teams.team_a + teams.team_b) == {1, 2, 3, 4}


@pytest.mark.asyncio
async def test_captain_close_has_two_random_captains(test_db):
    activity = await create_full_close(
        guild_id=200,
        team_mode=TEAM_MODE_CAPTAINS,
    )

    result = await start_close(
        guild_id=200,
        activity_id=activity.activity_id,
    )

    assert result.status == "started"
    assert result.captain_a_id in {1, 2, 3, 4}
    assert result.captain_b_id in {1, 2, 3, 4}
    assert result.captain_a_id != result.captain_b_id
    assert result.draft_turn in {"a", "b"}

    teams = await get_close_teams(activity.activity_id)

    assert len(teams.team_a) == 1
    assert len(teams.team_b) == 1
    assert len(teams.waiting) == 2
