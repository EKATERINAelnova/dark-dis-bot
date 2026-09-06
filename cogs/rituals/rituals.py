import discord

from discord import app_commands
from discord.ext import commands

from config.economy import CURRENCY_SYMBOL

from services.rituals import (
    perform_daily_ritual,
)

from utils.embeds import eden_embed


class Rituals(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="ритуал",
        description="Провести ежедневный ритуал сада",
    )
    @app_commands.guild_only()
    async def ritual(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        result = await perform_daily_ritual(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
        )

        if result.reward is None:
            hours = (
                result.remaining_seconds
                // 3600
            )

            minutes = (
                result.remaining_seconds
                % 3600
                // 60
            )

            embed = eden_embed(
                title="✦ RITUAL",
                description=(
                    "Сад пока молчит.\n\n"
                    "Вернуться к ритуалу можно через "
                    f"**{hours} ч. {minutes} мин.**"
                ),
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

            return

        reward = result.reward

        if reward.kind == "currency":
            reward_text = (
                f"**{reward.amount} "
                f"{CURRENCY_SYMBOL}**"
            )

        else:
            reward_text = (
                f"**{reward.amount} EDEN CASE**"
            )

        embed = eden_embed(
            title="✦ RITUAL COMPLETE",
            description=(
                "Сад ответил на твой зов.\n\n"
                f"Получено: {reward_text}"
            ),
        )

        embed.set_footer(
            text=(
                "Следующий ритуал будет доступен "
                "через 24 часа"
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
        Rituals(bot)
    )