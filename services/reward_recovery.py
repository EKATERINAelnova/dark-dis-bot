from dataclasses import dataclass, field

from services.activities import get_activity
from services.activity_rewards import ActivityRewardResult
from services.automatic_activity_rewards import (
    reward_duel_winner_automatically,
    reward_event_automatically,
)
from services.close_results import get_close_result
from services.close_rewards import reward_close_automatically
from services.duels import get_duel_result


@dataclass(frozen=True)
class RewardRecoveryResult:
    status: str
    activity_type: str | None = None
    rewards: list[ActivityRewardResult] = field(
        default_factory=list
    )


async def retry_activity_rewards(
    guild_id: int,
    activity_id: int,
    actor_id: int | None = None,
) -> RewardRecoveryResult:
    """
    Повторяет только автоматическую выдачу наград завершённой активности.

    Сами выплаты идемпотентны, а решения anti-farm policy для DUEL/CLOSE
    сохраняются отдельно, поэтому retry не меняет первоначальное решение.
    """

    activity = await get_activity(
        guild_id=guild_id,
        activity_id=activity_id,
    )

    if activity is None:
        return RewardRecoveryResult(
            status="not_found"
        )

    if activity.status != "finished":
        return RewardRecoveryResult(
            status="not_finished",
            activity_type=activity.type,
        )

    if activity.type == "event":
        rewards = await reward_event_automatically(
            activity=activity,
            actor_id=actor_id,
        )

    elif activity.type == "duel":
        result = await get_duel_result(
            activity_id
        )

        if (
            result is None
            or result.status != "confirmed"
        ):
            return RewardRecoveryResult(
                status="result_not_confirmed",
                activity_type=activity.type,
            )

        rewards = await reward_duel_winner_automatically(
            guild_id=guild_id,
            activity_id=activity_id,
            winner_id=result.winner_id,
            actor_id=actor_id,
        )

    elif activity.type == "close":
        result = await get_close_result(
            activity_id
        )

        if (
            result is None
            or result.status != "confirmed"
        ):
            return RewardRecoveryResult(
                status="result_not_confirmed",
                activity_type=activity.type,
            )

        rewards = await reward_close_automatically(
            guild_id=guild_id,
            activity_id=activity_id,
            actor_id=actor_id,
        )

    else:
        return RewardRecoveryResult(
            status="unsupported_type",
            activity_type=activity.type,
        )

    return RewardRecoveryResult(
        status="processed",
        activity_type=activity.type,
        rewards=rewards,
    )
