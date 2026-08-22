import discord

from database.economy import get_balance
from .bet_view import BetView
from config.economy import CURRENCY_SYMBOL
from utils.embeds import (
    casino_embed,
    error_embed,
)


class CasinoView(discord.ui.View):
    def __init__(
        self,
        player_id: int
    ):
        super().__init__(timeout=60)

        self.player_id = player_id
        self.selected_game: str | None = None

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужой стол",
                description="Эта игровая сессия принадлежит другому путнику.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False

        return True

    async def select_game(
        self,
        interaction: discord.Interaction,
        game: str,
        game_name: str
    ):
        # Если игру уже выбрали,
        # повторно выбрать другую нельзя.
        if self.selected_game is not None:
            embed = error_embed(
                title="Игра уже выбрана",
                description="Сначала закончи текущий выбор.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        # Сохраняем выбор до первого await,
        # чтобы два быстрых клика не выбрали две игры.
        self.selected_game = game

        # Получаем актуальный баланс игрока.
        balance = await get_balance(
            guild_id=interaction.guild.id,
            user_id=self.player_id
        )

        # Создаём следующий экран казино.
        bet_view = BetView(
            player_id=self.player_id,
            guild_id=interaction.guild.id,
            game=game,
            balance=balance
        )
        embed = casino_embed(
            title=game_name,
            description=(
                f"Баланс: **{balance} {CURRENCY_SYMBOL}**\n\n"
                "Выбери размер ставки."
            ),
        )
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=bet_view,
        )

        # CasinoView больше не нужен,
        # потому что его заменил BetView.
        self.stop()

    @discord.ui.button(
        label="Рулетка",
        emoji="🎡",
        style=discord.ButtonStyle.danger
    )
    async def roulette(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.select_game(
            interaction,
            game="roulette",
            game_name="🎡 Рулетка"
        )

    @discord.ui.button(
        label="Blackjack",
        emoji="🃏",
        style=discord.ButtonStyle.secondary
    )
    async def blackjack(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.select_game(
            interaction,
            game="blackjack",
            game_name="🃏 Blackjack"
        )

    @discord.ui.button(
        label="Слоты",
        emoji="🎰",
        style=discord.ButtonStyle.success
    )
    async def slots(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.select_game(
            interaction,
            game="slots",
            game_name="🎰 Слоты"
        )