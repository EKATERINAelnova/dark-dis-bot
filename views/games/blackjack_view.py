import secrets
import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import (
    payout,
    refund_bet,
    double_bet,
    place_bet
)

from .result_casino_view import CasinoResultView


SUITS = [
    "♠️",
    "♥️",
    "♦️",
    "♣️"
]

RANKS = [
    "2", "3", "4", "5", "6",
    "7", "8", "9", "10",
    "J", "Q", "K", "A"
]


# =========================================================
# БАЗОВАЯ VIEW
# =========================================================

class BlackjackBaseView(discord.ui.View):
    """
    Общая логика для игровых View Blackjack.
    """

    def __init__(
        self,
        player_id: int,
        timeout: float
    ):
        super().__init__(timeout=timeout)

        self.player_id = player_id
        self.processing = False

        # Сюда сохраняем сообщение,
        # чтобы иметь возможность изменить его при timeout.
        self.message = None

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Не позволяет другому пользователю
        нажимать кнопки чужой партии.
        """

        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "Это не твоя партия.",
                ephemeral=True
            )
            return False

        return True

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item
    ):
        """
        Любая ошибка View теперь не исчезает молча.
        """

        self.processing = False

        print(
            "[BLACKJACK VIEW ERROR]",
            type(error).__name__,
            str(error)
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    (
                        "Произошла ошибка Blackjack.\n"
                        "Попробуй открыть казино заново."
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    (
                        "Произошла ошибка Blackjack.\n"
                        "Попробуй открыть казино заново."
                    ),
                    ephemeral=True
                )

        except Exception as response_error:
            print(
                "[BLACKJACK ERROR RESPONSE FAILED]",
                repr(response_error)
            )

    def disable_all_buttons(self):
        """
        Выключает все кнопки View.
        """

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


# =========================================================
# ЭКРАН ПОСЛЕ ЗАВЕРШЕНИЯ ПАРТИИ
# =========================================================

class BlackjackResultView(BlackjackBaseView):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        bet: int
    ):
        super().__init__(
            player_id=player_id,
            timeout=180
        )

        self.guild_id = guild_id

        # Именно исходная ставка.
        # Double Down сюда не влияет.
        self.bet = bet

    async def begin_transition(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Безопасно начинает переход
        с ResultView на другую View.

        Возвращает True,
        если переход можно продолжить.
        """

        if self.processing:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Действие уже выполняется.",
                    ephemeral=True
                )

            return False

        self.processing = True

        # Сразу подтверждаем нажатие Discord.
        await interaction.response.defer()

        # Визуально выключаем старые кнопки,
        # чтобы нельзя было кликать несколько раз.
        self.disable_all_buttons()

        await interaction.edit_original_response(
            view=self
        )

        # Очень важный порядок:
        #
        # сначала убираем старую View из dispatcher,
        # потом будем регистрировать новую.
        self.stop()

        return True

    # =====================================================
    # ЕЩЁ РАЗ
    # =====================================================

    @discord.ui.button(
        label="Ещё раз",
        emoji="🔁",
        style=discord.ButtonStyle.success,
        custom_id="blackjack_play_again"
    )
    async def play_again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.begin_transition(interaction):
            return

        # Повторяем именно исходную ставку.
        new_balance = await place_bet(
            guild_id=self.guild_id,
            user_id=self.player_id,
            bet=self.bet,
            game="blackjack"
        )

        # Денег уже недостаточно.
        if new_balance is None:
            from ..bet_view import BetView

            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id
            )

            bet_view = BetView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                game="blackjack",
                balance=current_balance
            )

            await interaction.edit_original_response(
                content=(
                    "## 🃏 Blackjack\n\n"
                    "Недостаточно средств, чтобы "
                    "повторить предыдущую ставку.\n\n"
                    f"Баланс: "
                    f"**{current_balance} {CURRENCY_SYMBOL}**\n\n"
                    "Выберите другую ставку:"
                ),
                view=bet_view
            )

            return

        # Новая независимая партия.
        blackjack_view = BlackjackView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            bet=self.bet,
            balance_after_bet=new_balance
        )

        await blackjack_view.start_game(
            interaction
        )

    # =====================================================
    # ИЗМЕНИТЬ СТАВКУ
    # =====================================================

    @discord.ui.button(
        label="Изменить ставку",
        emoji="💰",
        style=discord.ButtonStyle.primary,
        custom_id="blackjack_change_bet"
    )
    async def change_bet(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.begin_transition(interaction):
            return

        # Импорт внутри callback защищает
        # от циклического импорта.
        from ..bet_view import BetView

        current_balance = await get_balance(
            guild_id=self.guild_id,
            user_id=self.player_id
        )

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game="blackjack",
            balance=current_balance
        )

        await interaction.edit_original_response(
            content=(
                "## 🃏 Blackjack\n\n"
                f"Баланс: "
                f"**{current_balance} {CURRENCY_SYMBOL}**\n\n"
                "Выберите ставку:"
            ),
            view=bet_view
        )

    # =====================================================
    # В КАЗИНО
    # =====================================================

    @discord.ui.button(
        label="В казино",
        emoji="🎰",
        style=discord.ButtonStyle.secondary,
        custom_id="blackjack_back_to_casino"
    )
    async def back_to_casino(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.begin_transition(interaction):
            return

        from ..casino_view import CasinoView

        casino_view = CasinoView(
            self.player_id
        )

        await interaction.edit_original_response(
            content=(
                "## 🍎 LOST EDEN CASINO\n\n"
                "Выбери игру:"
            ),
            view=casino_view
        )

    # =====================================================
    # TIMEOUT RESULT VIEW
    # =====================================================

    async def on_timeout(self):
        """
        После timeout результат остаётся,
        но кнопки больше не активны.
        """

        self.disable_all_buttons()

        if self.message is None:
            return

        try:
            await self.message.edit(
                view=self
            )

        except Exception as error:
            print(
                "[BLACKJACK RESULT TIMEOUT ERROR]",
                repr(error)
            )


# =========================================================
# ОСНОВНАЯ ИГРА
# =========================================================

class BlackjackView(BlackjackBaseView):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        bet: int,
        balance_after_bet: int
    ):
        super().__init__(
            player_id=player_id,
            timeout=120
        )

        self.guild_id = guild_id

        # Исходная выбранная ставка.
        # Не меняется после Double Down.
        self.base_bet = bet

        # Текущая общая ставка партии.
        # После Double Down может стать в два раза больше.
        self.bet = bet

        # Баланс после последнего списания ставки.
        self.balance_after_bet = balance_after_bet

        self.finished = False

        # =================================================
        # КОЛОДА
        # =================================================

        self.deck = [
            (rank, suit)
            for suit in SUITS
            for rank in RANKS
        ]

        secrets.SystemRandom().shuffle(
            self.deck
        )

        # Игрок получает две карты.
        self.player_hand = [
            self.draw_card(),
            self.draw_card()
        ]

        # Дилер получает две карты.
        self.dealer_hand = [
            self.draw_card(),
            self.draw_card()
        ]

        self.update_buttons()

    # =========================================================
    # КАРТЫ
    # =========================================================

    def draw_card(self):
        return self.deck.pop()

    @staticmethod
    def hand_value(hand) -> int:
        """
        Возвращает значение руки.

        Туз автоматически становится 1,
        если значение 11 вызывает перебор.
        """

        value = 0
        aces = 0

        for rank, suit in hand:
            if rank in ("J", "Q", "K"):
                value += 10

            elif rank == "A":
                value += 11
                aces += 1

            else:
                value += int(rank)

        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    @staticmethod
    def is_blackjack(hand) -> bool:
        """
        Натуральный Blackjack:
        ровно две карты и сумма 21.
        """

        return (
            len(hand) == 2
            and BlackjackView.hand_value(hand) == 21
        )

    def can_double(self) -> bool:
        """
        Double Down возможен только:

        - на первых двух картах;
        - если по сохранённому балансу
          хватает ещё на одну ставку.

        Реальная проверка всё равно
        выполняется в БД через double_bet().
        """

        return (
            len(self.player_hand) == 2
            and self.balance_after_bet >= self.bet
            and not self.finished
        )

    @staticmethod
    def format_hand(hand) -> str:
        return "  ".join(
            f"{rank}{suit}"
            for rank, suit in hand
        )

    # =========================================================
    # UI
    # =========================================================

    def render_table(
        self,
        show_dealer: bool = False
    ) -> str:
        player_cards = self.format_hand(
            self.player_hand
        )

        player_value = self.hand_value(
            self.player_hand
        )

        if show_dealer:
            dealer_cards = self.format_hand(
                self.dealer_hand
            )

            dealer_value = self.hand_value(
                self.dealer_hand
            )

            dealer_text = (
                f"{dealer_cards}\n"
                f"Счёт: **{dealer_value}**"
            )

        else:
            first_card = self.dealer_hand[0]

            dealer_text = (
                f"{first_card[0]}"
                f"{first_card[1]}  🂠"
            )

        return (
            "## 🃏 Blackjack\n\n"
            f"Ваша ставка: "
            f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
            "### Дилер\n"
            f"{dealer_text}\n\n"
            "### Вы\n"
            f"{player_cards}\n"
            f"Счёт: **{player_value}**"
        )

    def update_buttons(self):
        for item in self.children:
            if not isinstance(
                item,
                discord.ui.Button
            ):
                continue

            if item.custom_id == "blackjack_double":
                item.disabled = not self.can_double()

    async def ensure_action_available(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Не оставляет повторный клик
        без ответа Discord.
        """

        if self.finished:
            await interaction.response.send_message(
                "Эта партия уже завершена.",
                ephemeral=True
            )
            return False

        if self.processing:
            await interaction.response.send_message(
                "Предыдущее действие ещё выполняется.",
                ephemeral=True
            )
            return False

        self.processing = True

        return True

    # =========================================================
    # СТАРТ
    # =========================================================

    async def start_game(
        self,
        interaction: discord.Interaction
    ):
        player_blackjack = self.is_blackjack(
            self.player_hand
        )

        dealer_blackjack = self.is_blackjack(
            self.dealer_hand
        )

        # Blackjack у обоих.
        if player_blackjack and dealer_blackjack:
            await self.finish_result(
                interaction=interaction,
                result="push",
                reason="Blackjack у вас и у дилера."
            )
            return

        # Blackjack только у игрока.
        if player_blackjack:
            await self.finish_result(
                interaction=interaction,
                result="blackjack",
                reason="Натуральный Blackjack."
            )
            return

        # Blackjack только у дилера.
        if dealer_blackjack:
            await self.finish_result(
                interaction=interaction,
                result="loss",
                reason="У дилера Blackjack."
            )
            return

        self.update_buttons()

        self.message = await interaction.edit_original_response(
            content=self.render_table(),
            view=self
        )

    # =========================================================
    # РАСЧЁТ ДИЛЕРА
    # =========================================================

    def play_dealer(self):
        """
        Дилер стоит на 17.

        Это правило S17.
        """

        while self.hand_value(
            self.dealer_hand
        ) < 17:
            self.dealer_hand.append(
                self.draw_card()
            )

    def get_dealer_result(self):
        """
        Сравнивает готовые руки.

        Возвращает:
        ("win" | "loss" | "push", причина)
        """

        player_value = self.hand_value(
            self.player_hand
        )

        dealer_value = self.hand_value(
            self.dealer_hand
        )

        if dealer_value > 21:
            return (
                "win",
                "Дилер перебрал."
            )

        if player_value > dealer_value:
            return (
                "win",
                "Ваша рука сильнее руки дилера."
            )

        if player_value < dealer_value:
            return (
                "loss",
                "Дилер оказался ближе к 21."
            )

        return (
            "push",
            "У вас одинаковое количество очков."
        )

    async def dealer_turn(
        self,
        interaction: discord.Interaction
    ):
        self.play_dealer()

        result, reason = self.get_dealer_result()

        await self.finish_result(
            interaction=interaction,
            result=result,
            reason=reason
        )

    # =========================================================
    # ОБЩЕЕ ЗАВЕРШЕНИЕ
    # =========================================================

    async def build_result(
        self,
        result: str,
        reason: str
    ):
        """
        Выполняет финансовую часть
        и формирует финальный текст.
        """

        self.finished = True

        result_view = BlackjackResultView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            bet=self.base_bet
        )

        # =====================================================
        # ПРОИГРЫШ
        # =====================================================

        if result == "loss":
            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id
            )

            content = (
                self.render_table(
                    show_dealer=True
                )
                + "\n\n"
                + "### Проигрыш\n"
                + f"{reason}\n\n"
                + f"Потеряно: "
                + f"**{self.bet} "
                + f"{CURRENCY_SYMBOL}**\n"
                + f"Баланс: "
                + f"**{current_balance} "
                + f"{CURRENCY_SYMBOL}**"
            )

            return content, result_view

        # =====================================================
        # ОБЫЧНАЯ ПОБЕДА
        # =====================================================

        if result == "win":
            payout_amount = self.bet * 2

            new_balance = await payout(
                guild_id=self.guild_id,
                user_id=self.player_id,
                amount=payout_amount,
                game="blackjack",
                result="win"
            )

            content = (
                self.render_table(
                    show_dealer=True
                )
                + "\n\n"
                + "### Победа\n"
                + f"{reason}\n\n"
                + f"Выигрыш: "
                + f"**+{self.bet} "
                + f"{CURRENCY_SYMBOL}**\n"
                + f"Баланс: "
                + f"**{new_balance} "
                + f"{CURRENCY_SYMBOL}**"
            )

            return content, result_view

        # =====================================================
        # BLACKJACK
        # =====================================================

        if result == "blackjack":
            payout_amount = (
                self.bet * 5 + 1
            ) // 2

            new_balance = await payout(
                guild_id=self.guild_id,
                user_id=self.player_id,
                amount=payout_amount,
                game="blackjack",
                result="blackjack"
            )

            profit = (
                payout_amount
                - self.bet
            )

            content = (
                self.render_table(
                    show_dealer=True
                )
                + "\n\n"
                + "### 🃏 BLACKJACK!\n"
                + f"{reason}\n\n"
                + f"Выигрыш: "
                + f"**+{profit} "
                + f"{CURRENCY_SYMBOL}**\n"
                + f"Баланс: "
                + f"**{new_balance} "
                + f"{CURRENCY_SYMBOL}**"
            )

            return content, result_view

        # =====================================================
        # НИЧЬЯ
        # =====================================================

        if result == "push":
            new_balance = await refund_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="blackjack",
                reason="push"
            )

            content = (
                self.render_table(
                    show_dealer=True
                )
                + "\n\n"
                + "### Ничья\n"
                + f"{reason}\n"
                + "Ставка возвращена.\n\n"
                + f"Баланс: "
                + f"**{new_balance} "
                + f"{CURRENCY_SYMBOL}**"
            )

            return content, result_view

        raise ValueError(
            f"Неизвестный результат Blackjack: {result}"
        )

    async def finish_result(
        self,
        interaction: discord.Interaction,
        result: str,
        reason: str
    ):
        """
        Завершает партию через Discord interaction.
        """

        content, result_view = await self.build_result(
            result=result,
            reason=reason
        )

        self.processing = False

        # Критично:
        # старая View останавливается ДО регистрации новой.
        self.stop()

        message = await interaction.edit_original_response(
            content=content,
            view=result_view
        )

        result_view.message = message

    # =========================================================
    # HIT
    # =========================================================

    @discord.ui.button(
        label="Ещё",
        emoji="🃏",
        style=discord.ButtonStyle.primary,
        custom_id="blackjack_hit"
    )
    async def hit(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.ensure_action_available(
            interaction
        ):
            return

        await interaction.response.defer()

        self.player_hand.append(
            self.draw_card()
        )

        self.update_buttons()

        player_value = self.hand_value(
            self.player_hand
        )

        # Перебор.
        if player_value > 21:
            await self.finish_result(
                interaction=interaction,
                result="loss",
                reason="Перебор."
            )
            return

        # Ровно 21 автоматически завершает ход.
        if player_value == 21:
            await self.dealer_turn(
                interaction
            )
            return

        self.message = await interaction.edit_original_response(
            content=self.render_table(),
            view=self
        )

        self.processing = False

    # =========================================================
    # STAND
    # =========================================================

    @discord.ui.button(
        label="Хватит",
        emoji="✋",
        style=discord.ButtonStyle.secondary,
        custom_id="blackjack_stand"
    )
    async def stand(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.ensure_action_available(
            interaction
        ):
            return

        await interaction.response.defer()

        await self.dealer_turn(
            interaction
        )

    # =========================================================
    # DOUBLE DOWN
    # =========================================================

    @discord.ui.button(
        label="Удвоить",
        emoji="✖️",
        style=discord.ButtonStyle.success,
        custom_id="blackjack_double"
    )
    async def double(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.ensure_action_available(
            interaction
        ):
            return

        # ensure_action_available уже поставил
        # processing=True.
        #
        # Если Double невозможен,
        # нужно вернуть processing обратно.

        if not self.can_double():
            self.processing = False

            await interaction.response.send_message(
                (
                    "Удвоение сейчас недоступно.\n"
                    "Нужно иметь две карты и достаточно средств "
                    "для второй ставки."
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer()

        original_bet = self.bet

        new_balance = await double_bet(
            guild_id=self.guild_id,
            user_id=self.player_id,
            bet=original_bet
        )

        # Баланс мог измениться между
        # отображением кнопки и нажатием.
        if new_balance is None:
            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id
            )

            self.balance_after_bet = current_balance
            self.processing = False

            self.update_buttons()

            self.message = await interaction.edit_original_response(
                content=self.render_table(),
                view=self
            )

            await interaction.followup.send(
                (
                    "Недостаточно средств для удвоения.\n"
                    f"Нужно ещё: "
                    f"**{original_bet} "
                    f"{CURRENCY_SYMBOL}**"
                ),
                ephemeral=True
            )

            return

        # Double успешно принят.
        self.balance_after_bet = new_balance
        self.bet += original_bet

        # Ровно одна дополнительная карта.
        self.player_hand.append(
            self.draw_card()
        )

        self.update_buttons()

        player_value = self.hand_value(
            self.player_hand
        )

        # Перебор.
        if player_value > 21:
            await self.finish_result(
                interaction=interaction,
                result="loss",
                reason="Перебор после удвоения."
            )
            return

        # После Double ход игрока
        # автоматически заканчивается.
        await self.dealer_turn(
            interaction
        )

    # =========================================================
    # TIMEOUT
    # =========================================================

    async def on_timeout(self):
        """
        Если игрок ушёл и 120 секунд
        ничего не нажимает, партия не зависает
        и ставка не исчезает.

        Используем автоматический Stand.
        """

        if self.finished:
            return

        if self.processing:
            return

        if self.message is None:
            return

        self.processing = True

        try:
            self.play_dealer()

            result, reason = self.get_dealer_result()

            reason = (
                "Время вышло. "
                "Ход автоматически завершён.\n"
                + reason
            )

            content, result_view = await self.build_result(
                result=result,
                reason=reason
            )

            self.processing = False

            message = await self.message.edit(
                content=content,
                view=result_view
            )

            result_view.message = message

        except Exception as error:
            self.processing = False

            print(
                "[BLACKJACK TIMEOUT ERROR]",
                type(error).__name__,
                str(error)
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__
            )