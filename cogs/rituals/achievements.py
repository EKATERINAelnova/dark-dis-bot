import discord

from discord import app_commands
from discord.ext import commands

from config.economy import CURRENCY_SYMBOL
from services.achievement_progress import (
    get_achievement_progress,
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

        snapshot = await get_achievement_progress(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            refresh=True,
        )

        lines = []

        for item in snapshot.items:
            achievement = item.achievement

            if item.unlocked:
                icon = "◆"
                progress_text = "Открыто"
            else:
                icon = "◇"

                if achievement.metric == "voice":
                    progress_text = (
                        f"{item.value // 60} / "
                        f"{achievement.target // 60} мин."
                    )

                elif achievement.minimum_participations > 0:
                    if (
                        item.participations
                        < achievement.minimum_participations
                    ):
                        progress_text = (
                            f"{item.participations} / "
                            f"{achievement.minimum_participations} матчей"
                        )
                    else:
                        progress_text = (
                            f"{item.value}% / {achievement.target}%"
                        )

                else:
                    progress_text = (
                        f"{min(item.value, achievement.target)} "
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
                    f"`{progress_text}` · "
                    f"Награда: **{reward_text}**"
                )
            )

        intro = ""
        if snapshot.unlocked_now:
            names = ", ".join(
                achievement.name
                for achievement in snapshot.unlocked_now
            )
            intro = (
                f"Сад открыл новые достижения: **{names}**.\n\n"
            )

        embed = eden_embed(
            title="✦ ACHIEVEMENTS",
            description=(
                intro
                + "\n\n".join(lines)
            ),
        )

        embed.set_footer(
            text=(
                f"LOST EDEN · RIMAY  •  "
                f"{snapshot.unlocked_count}/"
                f"{snapshot.total_count} открыто"
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
