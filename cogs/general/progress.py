import discord

from discord import app_commands
from discord.ext import commands

from services.activity_progress import (
    get_member_activity_progress,
)

from utils.embeds import eden_embed


class Progress(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="прогресс",
        description="Посмотреть прогресс участника сада",
    )
    @app_commands.guild_only()
    async def progress(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        if interaction.guild is None:
            return

        if user is None:
            user = interaction.user

        await interaction.response.defer()

        progress = await get_member_activity_progress(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        embed = eden_embed(
            title="✦ ПУТЬ В САДУ",
            description=(
                f"Прогресс {user.mention} в активностях LOST EDEN."
            ),
        )

        embed.add_field(
            name="EVENTS",
            value=(
                f"Участий: **{progress.events.participations}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="DUELS",
            value=(
                f"Сыграно: **{progress.duels.participations}**\n"
                f"Побед: **{progress.duels.wins}**\n"
                f"Winrate: **{progress.duels.winrate}%**"
            ),
            inline=False,
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.set_footer(
            text="Учитываются только завершённые и подтверждённые активности"
        )

        await interaction.followup.send(
            embed=embed
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Progress(bot)
    )
