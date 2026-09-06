import discord

from discord import app_commands
from discord.ext import commands

from cogs.events.list_helpers import (
    build_duel_list_embed,
    build_event_list_embed,
)

from services.activity_queries import (
    get_active_activities,
)


class ActivityLists(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="event-list",
        description="Показать активные серверные ивенты",
    )
    @app_commands.guild_only()
    async def event_list(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activities = await get_active_activities(
            guild_id=interaction.guild.id,
            activity_type="event",
        )

        embed = await build_event_list_embed(
            activities
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    @app_commands.command(
        name="duel-list",
        description="Показать активные дуэли",
    )
    @app_commands.guild_only()
    async def duel_list(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activities = await get_active_activities(
            guild_id=interaction.guild.id,
            activity_type="duel",
        )

        embed = await build_duel_list_embed(
            activities
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        ActivityLists(bot)
    )
