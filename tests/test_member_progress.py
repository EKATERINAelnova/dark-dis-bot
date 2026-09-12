import pytest

import services.level_roles as level_roles
from database.member_stats import add_xp
from services.member_progress import get_member_progress


@pytest.mark.asyncio
async def test_member_progress_combines_level_and_activity(test_db, monkeypatch):
    monkeypatch.setattr(
        level_roles,
        "LEVEL_ROLES",
        {
            2: "Milestone Two",
            5: "Milestone Five",
        },
    )

    new_xp, new_level, cases_gained = await add_xp(
        guild_id=500,
        user_id=42,
        amount=250,
    )

    assert new_xp == 250
    assert new_level == 2
    assert cases_gained == 1

    progress = await get_member_progress(
        guild_id=500,
        user_id=42,
    )

    assert progress.level == 2
    assert progress.rank == 1
    assert progress.xp_to_next_level == 50
    assert progress.stats.eden_cases == 1
    assert progress.current_milestone == (2, "Milestone Two")
    assert progress.next_milestone == (5, "Milestone Five")
    assert progress.activities.events.participations == 0
    assert progress.activities.duels.participations == 0
    assert progress.activities.closes.participations == 0
