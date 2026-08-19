import discord

from database.economy import get_balance
from .bet_view import BetView
from config.economy import CURRENCY_SYMBOL


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
            await interaction.response.send_message(
                "Это не твоё казино.",
                ephemeral=True
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
            await interaction.response.send_message(
                "Игра уже выбрана.",
                ephemeral=True
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

        await interaction.response.edit_message(
            content=(
                f"## {game_name}\n\n"
                f"Баланс: **{balance} {CURRENCY_SYMBOL}**\n\n"
                "Выбери ставку:"
            ),
            view=bet_view
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