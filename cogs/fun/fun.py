import random

import discord
from discord import app_commands
from discord.ext import commands
from views.coin_view import CoinView
from views.casino_view import CasinoView

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="roll",
        description="Бросить случайное число"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        max_value: app_commands.Range[int, 1, 1000]
    ):
        r = random.randint(1, max_value)
        await interaction.response.send_message(f"Выпало: {r}")

    @app_commands.command(
        name="coin",
        description="Подбросить монетку"
    )
    async def coin(self, interaction: discord.Interaction):
        view = CoinView(interaction.user.id)

        await interaction.response.send_message(
            "Выбери сторону:",
            view=view
        )
        random.choice(["Орёл", "Решка"])

    @app_commands.command(
        name="casino",
        description="Азартные игры - это плохо"
    )
    async def casino(
        self,
        interaction: discord.Interaction
    ):
        view = CasinoView(
            interaction.user.id
        )

        await interaction.response.send_message(
            "🎰 **LOST EDEN CASINO**\n\n"
            "Выбери игру:",
            view=view
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))