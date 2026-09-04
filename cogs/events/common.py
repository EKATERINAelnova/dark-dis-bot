import discord

from discord.ext import commands

from services.activities import (
    Activity,
    get_activity,
)


async def get_activity_for_command(
    interaction: discord.Interaction,
    activity_id: int,
    activity_type: str,
) -> Activity | None:
    if interaction.guild is None:
        return None

    activity = await get_activity(
        guild_id=interaction.guild.id,
        activity_id=activity_id,
    )

    if (
        activity is None
        or activity.type != activity_type
    ):
        await interaction.followup.send(
            (
                f"Такой "
                f"{activity_type.upper()} "
                f"не найден."
            ),
            ephemeral=True,
        )

        return None

    return activity


async def fetch_activity_message(
    bot: commands.Bot,
    activity: Activity,
) -> discord.Message | None:
    if (
        activity.channel_id is None
        or activity.message_id is None
    ):
        return None

    channel = bot.get_channel(
        activity.channel_id
    )

    if (
        channel is None
        or not hasattr(
            channel,
            "fetch_message",
        )
    ):
        return None

    try:
        return await channel.fetch_message(
            activity.message_id
        )

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException,
    ):
        return None