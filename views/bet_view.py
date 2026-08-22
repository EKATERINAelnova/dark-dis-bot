import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import place_bet
from utils.embeds import (
    casino_embed,
    error_embed,
    warning_embed,
)

from .games.roulette_view import RouletteView
from .games.blackjack_view import BlackjackView
from .games.slots_view import SlotsView


GAME_NAMES = {
    "roulette": "🎡 Рулетка",
    "blackjack": "🃏 Blackjack",
    "slots": "🎰 Слоты",
}


class BetView(discord.ui.View):
    """
    Экран выбора размера ставки.

    Деньги здесь не списываются.
    Игрок только выбирает сумму.
    """

    def __init__(
        self,
        player_id: int,
        guild_id: int,
        game: str,
        balance: int,
    ):
        super().__init__(timeout=60)

        self.player_id = player_id
        self.guild_id = guild_id
        self.game = game
        self.balance = balance

        self.disable_unavailable_bets()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Запрещаем взаимодействовать
        с чужим казино.
        """

        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая игра",
                description=(
                    "Эта ставка принадлежит другому игроку."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False

        return True

    def disable_unavailable_bets(self):
        """
        Отключаем ставки,
        превышающие текущий баланс.
        """

        for item in self.children:
            if not isinstance(
                item,
                discord.ui.Button,
            ):
                continue

            if item.custom_id is None:
                continue

            if not item.custom_id.startswith(
                "casino_bet_"
            ):
                continue

            bet = int(
                item.custom_id.removeprefix(
                    "casino_bet_"
                )
            )

            if bet > self.balance:
                item.disabled = True

    async def select_bet(
        self,
        interaction: discord.Interaction,
        bet: int,
    ):
        """
        Переходим к подтверждению ставки.

        Деньги всё ещё не списываются.
        """

        if bet > self.balance:
            embed = error_embed(
                title="Недостаточно средств",
                description=(
                    "Для этой ставки "
                    "не хватает средств.\n\n"
                    f"Баланс: "
                    f"**{self.balance} "
                    f"{CURRENCY_SYMBOL}**"
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        confirm_view = BetConfirmView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game=self.game,
            bet=bet,
        )

        game_name = GAME_NAMES[self.game]

        embed = casino_embed(
            title=game_name,
            description=(
                "Проверь ставку перед началом игры."
            ),
        )

        embed.add_field(
            name="Баланс",
            value=(
                f"**{self.balance} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Ставка",
            value=(
                f"**{bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Подтверждение",
            value=(
                "После начала игры "
                "ставка будет зафиксирована."
            ),
            inline=False,
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=confirm_view,
        )

        self.stop()

    @discord.ui.button(
        label="10",
        emoji=CURRENCY_SYMBOL,
        style=discord.ButtonStyle.secondary,
        custom_id="casino_bet_10",
    )
    async def bet_10(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_bet(
            interaction,
            10,
        )

    @discord.ui.button(
        label="25",
        emoji=CURRENCY_SYMBOL,
        style=discord.ButtonStyle.secondary,
        custom_id="casino_bet_25",
    )
    async def bet_25(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_bet(
            interaction,
            25,
        )

    @discord.ui.button(
        label="50",
        emoji=CURRENCY_SYMBOL,
        style=discord.ButtonStyle.primary,
        custom_id="casino_bet_50",
    )
    async def bet_50(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_bet(
            interaction,
            50,
        )

    @discord.ui.button(
        label="100",
        emoji=CURRENCY_SYMBOL,
        style=discord.ButtonStyle.primary,
        custom_id="casino_bet_100",
    )
    async def bet_100(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.select_bet(
            interaction,
            100,
        )


class BetConfirmView(discord.ui.View):
    """
    Экран подтверждения ставки.

    После нажатия "Играть" размер ставки
    считается зафиксированным.

    Для рулетки деньги будут списаны
    непосредственно при выборе сектора.
    """

    def __init__(
        self,
        player_id: int,
        guild_id: int,
        game: str,
        bet: int,
    ):
        super().__init__(timeout=60)

        self.player_id = player_id
        self.guild_id = guild_id
        self.game = game
        self.bet = bet

        self.processing = False

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая игра",
                description=(
                    "Эта ставка принадлежит "
                    "другому игроку."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Играть",
        emoji="✅",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        """
        Подтверждаем ставку
        и переходим непосредственно в игру.
        """
        if self.processing:
            embed = warning_embed(
                title="Игра запускается",
                description="Предыдущий переход ещё не завершён.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        self.processing = True

        # =====================================================
        # ROULETTE
        # =====================================================

        if self.game == "roulette":
            roulette_view = RouletteView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
            )

            embed = casino_embed(
                title="🎡 Рулетка",
                description=(
                    "Колесо ждёт выбора.\n\n"
                    f"Ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    "Выбери сектор:"
                ),
            )

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=roulette_view,
            )

            self.stop()
            return

        # =====================================================
        # BLACKJACK
        # =====================================================

        if self.game == "blackjack":
            await interaction.response.defer()

            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="blackjack",
            )

            if new_balance is None:
                self.processing = False

                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                bet_view = BetView(
                    player_id=self.player_id,
                    guild_id=self.guild_id,
                    game=self.game,
                    balance=current_balance,
                )

                await interaction.edit_original_response(
                    content=(
                        "## 🃏 Blackjack\n\n"
                        "Недостаточно средств "
                        "для этой ставки.\n\n"
                        f"Баланс: "
                        f"**{current_balance} "
                        f"{CURRENCY_SYMBOL}**\n\n"
                        "Выберите другую ставку:"
                    ),
                    embed=None,
                    view=bet_view,
                )

                self.stop()
                return

            blackjack_view = BlackjackView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance,
            )

            await blackjack_view.start_game(
                interaction
            )

            self.stop()
            return

        # =====================================================
        # SLOTS
        # =====================================================

        if self.game == "slots":
            await interaction.response.defer()

            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="slots",
            )

            if new_balance is None:
                self.processing = False

                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                bet_view = BetView(
                    player_id=self.player_id,
                    guild_id=self.guild_id,
                    game=self.game,
                    balance=current_balance,
                )

                await interaction.edit_original_response(
                    content=(
                        "## 🎰 Слоты\n\n"
                        "Недостаточно средств "
                        "для этой ставки.\n\n"
                        f"Баланс: "
                        f"**{current_balance} "
                        f"{CURRENCY_SYMBOL}**\n\n"
                        "Выберите другую ставку:"
                    ),
                    embed=None,
                    view=bet_view,
                )

                self.stop()
                return

            slots_view = SlotsView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance,
            )

            await interaction.edit_original_response(
                content=(
                    "## 🎰 Слоты\n\n"
                    f"Ваша ставка: "
                    f"**{self.bet} "
                    f"{CURRENCY_SYMBOL}**\n\n"
                    "Запускаем барабаны..."
                ),
                embed=None,
                view=None,
            )

            await slots_view.play(
                interaction
            )

            self.stop()
            return

        self.processing = False

        await interaction.response.send_message(
            "Неизвестная игра.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Изменить ставку",
        emoji="↩️",
        style=discord.ButtonStyle.secondary,
    )
    async def back(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        """
        Пока ставка не подтверждена,
        её можно изменить.
        """

        if self.processing:
            await interaction.response.send_message(
                "Игра уже запускается.",
                ephemeral=True,
            )
            return

        current_balance = await get_balance(
            guild_id=self.guild_id,
            user_id=self.player_id,
        )

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game=self.game,
            balance=current_balance,
        )

        game_name = GAME_NAMES[self.game]

        await interaction.response.edit_message(
            content=(
                f"## {game_name}\n\n"
                f"Баланс: "
                f"**{current_balance} "
                f"{CURRENCY_SYMBOL}**\n\n"
                "Выберите ставку:"
            ),
            embed=None,
            view=bet_view,
        )

        self.stop()