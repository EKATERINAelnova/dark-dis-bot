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


# =========================================================
# ВЫБОР СТАВКИ
# =========================================================

class BetView(discord.ui.View):
    """
    Экран выбора размера ставки.

    На этом этапе деньги не списываются.
    Игрок только выбирает размер ставки.
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

    # =====================================================
    # ЗАЩИТА VIEW
    # =====================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Не позволяет другим пользователям
        нажимать кнопки чужой игры.
        """

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

    # =====================================================
    # ДОСТУПНОСТЬ СТАВОК
    # =====================================================

    def disable_unavailable_bets(self):
        """
        Отключает кнопки ставок,
        превышающих текущий баланс.
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

    # =====================================================
    # ВЫБОР СТАВКИ
    # =====================================================

    async def select_bet(
        self,
        interaction: discord.Interaction,
        bet: int,
    ):
        """
        Переходит к подтверждению ставки.

        Деньги всё ещё не списываются.
        """

        # Дополнительная защита,
        # даже если кнопка почему-то не была disabled.
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

        game_name = GAME_NAMES.get(
            self.game,
            "🎰 Казино",
        )

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

    # =====================================================
    # КНОПКИ СТАВОК
    # =====================================================

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


# =========================================================
# ПОДТВЕРЖДЕНИЕ СТАВКИ
# =========================================================

class BetConfirmView(discord.ui.View):
    """
    Экран подтверждения ставки.

    После нажатия "Играть"
    размер ставки считается зафиксированным.

    Roulette:
        ставка списывается после выбора сектора.

    Blackjack / Slots:
        ставка списывается при запуске игры.
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

    # =====================================================
    # ЗАЩИТА VIEW
    # =====================================================

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

    # =====================================================
    # НЕДОСТАТОЧНО СРЕДСТВ
    # =====================================================

    async def show_insufficient_balance(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ):
        """
        Возвращает пользователя
        к выбору ставки после неудачного списания.
        """

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game=self.game,
            balance=current_balance,
        )

        game_name = GAME_NAMES.get(
            self.game,
            "🎰 Казино",
        )

        embed = casino_embed(
            title=game_name,
            description=(
                "Недостаточно средств "
                "для этой ставки.\n\n"
                f"Баланс: "
                f"**{current_balance} "
                f"{CURRENCY_SYMBOL}**\n\n"
                "Выбери другую ставку:"
            ),
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=bet_view,
        )

    # =====================================================
    # ИГРАТЬ
    # =====================================================

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
        Фиксирует ставку
        и запускает выбранную игру.
        """

        if self.processing:
            embed = warning_embed(
                title="Игра запускается",
                description=(
                    "Предыдущий переход "
                    "ещё не завершён."
                ),
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
                    f"**{self.bet} "
                    f"{CURRENCY_SYMBOL}**\n\n"
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
            # Подтверждаем interaction,
            # потому что дальше идут запросы к БД.
            await interaction.response.defer()

            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="blackjack",
            )

            # Баланс мог измениться
            # после выбора ставки.
            if new_balance is None:
                self.processing = False

                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                await self.show_insufficient_balance(
                    interaction,
                    current_balance,
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
            # Slots тоже выполняют работу после клика,
            # поэтому заранее подтверждаем interaction.
            await interaction.response.defer()

            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="slots",
            )

            # Баланс мог измениться
            # после выбора ставки.
            if new_balance is None:
                self.processing = False

                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                await self.show_insufficient_balance(
                    interaction,
                    current_balance,
                )

                self.stop()
                return

            slots_view = SlotsView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance,
            )

            # Никакого промежуточного content.
            # SlotsView сам создаёт первый embed.
            await slots_view.play(
                interaction
            )

            self.stop()
            return

        # =====================================================
        # НЕИЗВЕСТНАЯ ИГРА
        # =====================================================

        self.processing = False

        embed = error_embed(
            title="Ошибка казино",
            description=(
                "Не удалось определить "
                "выбранную игру."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # =====================================================
    # ИЗМЕНИТЬ СТАВКУ
    # =====================================================

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
            embed = warning_embed(
                title="Игра запускается",
                description=(
                    "Предыдущий переход "
                    "ещё не завершён."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
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

        game_name = GAME_NAMES.get(
            self.game,
            "🎰 Казино",
        )

        embed = casino_embed(
            title=game_name,
            description=(
                f"Баланс: "
                f"**{current_balance} "
                f"{CURRENCY_SYMBOL}**\n\n"
                "Выбери ставку:"
            ),
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=bet_view,
        )

        self.stop()