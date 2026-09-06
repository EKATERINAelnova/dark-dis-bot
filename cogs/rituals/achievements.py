import discord

from discord import app_commands
from discord.ext import commands

from config.economy import CURRENCY_SYMBOL

from database.member_stats import get_member_stats

from services.achievements import (
    ACHIEVEMENTS,
    check_achievements,
    get_achievement_value,
    get_unlocked_achievement_keys,
)

from utils.embeds import eden_embed


class Achievements(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="достижения",
        description="Посмотреть достижения участника сада",
    )
    @app_commands.guild_only()
    async def achievements(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        await check_achievements(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
        )

        stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
        )

        unlocked_keys = await get_unlocked_achievement_keys(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
        )

        lines = []

        for achievement in ACHIEVEMENTS:
            unlocked = (
                achievement.key
                in unlocked_keys
            )

            value = get_achievement_value(
                achievement,
                stats,
            )

            if unlocked:
                icon = "◆"
                progress = "Открыто"

            else:
                icon = "◇"

                if achievement.metric == "voice":
                    progress = (
                        f"{value // 60} / "
                        f"{achievement.target // 60} мин."
                    )

                else:
                    progress = (
                        f"{min(value, achievement.target)} "
                        f"/ {achievement.target}"
                    )

            if achievement.reward_kind == "currency":
                reward_text = (
                    f"{achievement.reward_amount} "
                    f"{CURRENCY_SYMBOL}"
                )

            else:
                reward_text = (
                    f"{achievement.reward_amount} "
                    f"EDEN CASE"
                )

            lines.append(
                (
                    f"{icon} **{achievement.name}**\n"
                    f"{achievement.description}\n"
                    f"`{progress}` · "
                    f"Награда: **{reward_text}**"
                )
            )

        embed = eden_embed(
            title="✦ ACHIEVEMENTS",
            description="\n\n".join(
                lines
            ),
        )

        embed.set_footer(
            text=(
                f"LOST EDEN · RIMAY  •  "
                f"{len(unlocked_keys)}/"
                f"{len(ACHIEVEMENTS)} открыто"
            )
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Achievements(bot)
    )