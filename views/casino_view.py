import discord

from database.economy import get_balance
from .bet_view import BetView

from config.economy import (
    CURRENCY_SYMBOL,
    CASINO_MIN_BET,
)

from utils.embeds import (
    casino_embed,
    error_embed,
)


class CasinoView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
    ):
        super().__init__(timeout=60)

        self.player_id = player_id

        # Защищает от двойного выбора игры.
        self.selected_game: str | None = None

    # =========================================================
    # ЗАЩИТА VIEW
    # =========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Не позволяет другим пользователям
        пользоваться чужим казино.
        """

        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужой стол",
                description=(
                    "Эта игровая сессия "
                    "принадлежит другому путнику."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return False

        return True

    # =========================================================
    # ВЫБОР ИГРЫ
    # =========================================================

    async def select_game(
        self,
        interaction: discord.Interaction,
        game: str,
        game_name: str,
    ):
        """
        Выбирает игру казино
        и открывает экран ставок.
        """

        # =====================================================
        # ЗАЩИТА ОТ ДВОЙНОГО КЛИКА
        # =====================================================

        if self.selected_game is not None:
            embed = error_embed(
                title="Игра уже выбрана",
                description=(
                    "Сначала закончи текущий выбор."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        # Сохраняем выбор до первого await,
        # чтобы два быстрых клика
        # не могли открыть две игры.
        self.selected_game = game

        # =====================================================
        # GUILD
        # =====================================================

        if interaction.guild is None:
            self.selected_game = None

            embed = error_embed(
                title="Казино недоступно",
                description=(
                    "Казино можно использовать "
                    "только на сервере."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        guild_id = interaction.guild.id

        # =====================================================
        # БАЛАНС
        # =====================================================

        balance = await get_balance(
            guild_id=guild_id,
            user_id=self.player_id,
        )

        # =====================================================
        # НЕДОСТАТОЧНО СРЕДСТВ
        # =====================================================

        if balance < CASINO_MIN_BET:
            embed = error_embed(
                title="Недостаточно средств",
                description=(
                    "Для игры в казино "
                    "не хватает средств.\n\n"
                    f"Минимальная ставка: "
                    f"**{CASINO_MIN_BET} "
                    f"{CURRENCY_SYMBOL}**\n"
                    f"Твой баланс: "
                    f"**{balance} "
                    f"{CURRENCY_SYMBOL}**"
                ),
            )

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=None,
            )

            self.stop()
            return

        # =====================================================
        # ЭКРАН ВЫБОРА СТАВКИ
        # =====================================================

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=guild_id,
            game=game,
            balance=balance,
        )

        embed = casino_embed(
            title=game_name,
            description=(
                f"Баланс: "
                f"**{balance} "
                f"{CURRENCY_SYMBOL}**\n\n"
                "Выбери размер ставки."
            ),
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=bet_view,
        )

        # CasinoView больше не нужна,
        # потому что её заменил BetView.
        self.stop()

    # =========================================================
    # РУЛЕТКА
    # =========================================================

    @discord.ui.button(
        label="Рулетка",
        emoji="🎡",
        style=discord.ButtonStyle.danger,
    )
    async def roulette(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_game(
            interaction,
            game="roulette",
            game_name="🎡 Рулетка",
        )

    # =========================================================
    # BLACKJACK
    # =========================================================

    @discord.ui.button(
        label="Blackjack",
        emoji="🃏",
        style=discord.ButtonStyle.secondary,
    )
    async def blackjack(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_game(
            interaction,
            game="blackjack",
            game_name="🃏 Blackjack",
        )

    # =========================================================
    # SLOTS
    # =========================================================

    @discord.ui.button(
        label="Слоты",
        emoji="🎰",
        style=discord.ButtonStyle.success,
    )
    async def slots(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_game(
            interaction,
            game="slots",
            game_name="🎰 Слоты",
        )