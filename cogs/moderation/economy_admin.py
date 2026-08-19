import discord

from discord import app_commands
from discord.ext import commands

from config.economy import (
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
    REASON_ADMIN
)
from database.economy import change_balance


class EconomyAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="addseeds",
        description="Добавить Seeds пользователю"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_seeds(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[int, 1, 100000]
    ):
        new_balance = await change_balance(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=amount,
            reason=REASON_ADMIN,
            description="admin_add",
            actor_id=interaction.user.id
        )

        await interaction.response.send_message(
            (
                f"Баланс {user.mention} увеличен "
                f"на **{amount} {CURRENCY_SYMBOL}**.\n"
                f"Новый баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            ),
            ephemeral=True
        )

    @app_commands.command(
        name="removeseeds",
        description="Уменьшить Seeds пользователя"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_seeds(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[int, 1, 100000]
    ):
        new_balance = await change_balance(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=-amount,
            reason=REASON_ADMIN,
            description="admin_remove",
            actor_id=interaction.user.id
        )

        if new_balance is None:
            await interaction.response.send_message(
                (
                    f"У {user.mention} недостаточно "
                    f"{CURRENCY_NAME}.\n"
                    f"Нельзя снять "
                    f"**{amount} {CURRENCY_SYMBOL}**."
                ),
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            (
                f"Баланс {user.mention} уменьшен "
                f"на **{amount} {CURRENCY_SYMBOL}**.\n"
                f"Новый баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            ),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyAdmin(bot))