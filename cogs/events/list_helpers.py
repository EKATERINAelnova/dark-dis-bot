import discord

from cogs.events.reward_helpers import (
    format_event_reward_preset,
)

from services.activities import (
    Activity,
    get_activity_participants,
)

from services.duels import (
    get_duel_players,
)

from utils.embeds import eden_embed


STATUS_NAMES = {
    "open": "OPEN",
    "running": "IN PROGRESS",
}


async def build_event_list_embed(
    activities: list[Activity],
) -> discord.Embed:
    embed = eden_embed(
        title="✦ ACTIVE EVENTS",
        description=(
            "Открытые и проходящие события сада."
        ),
    )

    if not activities:
        embed.description = (
            "Сейчас активных EVENT нет."
        )
        return embed

    for activity in activities:
        participants = await get_activity_participants(
            activity.activity_id
        )

        status = STATUS_NAMES.get(
            activity.status,
            activity.status.upper(),
        )

        if activity.max_participants is None:
            participants_text = str(
                len(participants)
            )
        else:
            participants_text = (
                f"{len(participants)} / "
                f"{activity.max_participants}"
            )

        reward_text = format_event_reward_preset(
            activity.reward_preset
        ).replace("\n", " · ")

        embed.add_field(
            name=(
                f"#{activity.activity_id} · "
                f"{activity.title}"
            ),
            value=(
                f"`{status}` · "
                f"Участники: **{participants_text}**\n"
                f"Награда: {reward_text}"
            ),
            inline=False,
        )

    return embed


async def build_duel_list_embed(
    activities: list[Activity],
) -> discord.Embed:
    embed = eden_embed(
        title="✦ ACTIVE DUELS",
        description=(
            "Текущие вызовы и дуэли сада."
        ),
    )

    if not activities:
        embed.description = (
            "Сейчас активных DUEL нет."
        )
        return embed

    for activity in activities:
        players = await get_duel_players(
            activity.activity_id
        )

        if players is None:
            continue

        challenger_id, opponent_id = players

        status = STATUS_NAMES.get(
            activity.status,
            activity.status.upper(),
        )

        embed.add_field(
            name=f"DUEL #{activity.activity_id}",
            value=(
                f"<@{challenger_id}> ⚔ <@{opponent_id}>\n"
                f"`{status}`"
            ),
            inline=False,
        )

    if not embed.fields:
        embed.description = (
            "Сейчас активных DUEL нет."
        )

    return embed
