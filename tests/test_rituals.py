import pytest

import services.rituals as rituals
from database.member_stats import get_member_stats
from services.rituals import (
    RITUAL_COOLDOWN,
    RitualReward,
    get_daily_ritual_status,
    perform_daily_ritual,
)


@pytest.mark.asyncio
async def test_daily_ritual_respects_cooldown(test_db, monkeypatch):
    guild_id = 800
    user_id = 88
    started_at = 100_000

    monkeypatch.setattr(
        rituals,
        "roll_ritual_reward",
        lambda: RitualReward(
            kind="currency",
            amount=20,
            weight=1,
        ),
    )

    first = await perform_daily_ritual(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at,
    )

    assert first.reward is not None
    assert first.reward.amount == 20

    second = await perform_daily_ritual(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at + 3600,
    )

    assert second.reward is None
    assert second.remaining_seconds == RITUAL_COOLDOWN - 3600

    status = await get_daily_ritual_status(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at + 3600,
    )

    assert status.available is False
    assert status.remaining_seconds == RITUAL_COOLDOWN - 3600

    stats = await get_member_stats(
        guild_id=guild_id,
        user_id=user_id,
    )
    assert stats.currency == 20


@pytest.mark.asyncio
async def test_daily_ritual_available_again_after_24_hours(test_db, monkeypatch):
    guild_id = 801
    user_id = 89
    started_at = 200_000

    monkeypatch.setattr(
        rituals,
        "roll_ritual_reward",
        lambda: RitualReward(
            kind="currency",
            amount=10,
            weight=1,
        ),
    )

    await perform_daily_ritual(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at,
    )

    status = await get_daily_ritual_status(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at + RITUAL_COOLDOWN,
    )

    assert status.available is True
    assert status.remaining_seconds == 0

    second = await perform_daily_ritual(
        guild_id=guild_id,
        user_id=user_id,
        current_time=started_at + RITUAL_COOLDOWN,
    )

    assert second.reward is not None

    stats = await get_member_stats(
        guild_id=guild_id,
        user_id=user_id,
    )
    assert stats.currency == 20
