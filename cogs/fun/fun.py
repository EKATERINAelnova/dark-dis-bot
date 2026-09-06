import random

import discord
from discord import app_commands
from discord.ext import commands
from views.coin_view import CoinView
from views.casino_view import CasinoView
from utils.embeds import (
    eden_embed,
    casino_embed,
)

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="бросок",
        description="Бросить случайное число"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        max_value: app_commands.Range[int, 1, 1000]
    ):
        r = random.randint(1, max_value)

        embed = eden_embed(
            title="🎲 Бросок судьбы",
            description=(
                "Сад выбрал число...\n\n"
                f"## {r}\n"
                f"*из {max_value}*"
            ),
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="монета",
        description="Подбросить монетку"
    )
    async def coin(self, interaction: discord.Interaction):
        view = CoinView(interaction.user.id)

        embed = eden_embed(
        title="Монета Эдема",
        description=(
            "Выбери сторону монеты.\n\n"
            "*Иногда судьба решается одним броском.*"
        ),
        )

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

    @app_commands.command(
        name="казино",
        description="Азартные игры - это плохо"
    )
    async def casino(
        self,
        interaction: discord.Interaction
    ):
        view = CasinoView(
            interaction.user.id
        )

        embed = casino_embed(
            title="🎰 LOST EDEN CASINO",
            description=(
                "Добро пожаловать за столы сада.\n\n"
                "Выбери игру:"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))