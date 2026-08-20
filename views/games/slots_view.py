import asyncio
import secrets
import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from services.casino import payout
from .result_casino_view import CasinoResultView


# =========================================================
# СИМВОЛЫ
# =========================================================

SYMBOLS = {
    "🌿": 35,
    "🍎": 28,
    "🌹": 18,
    "💎": 12,
    "🐍": 7
}


PAYOUTS = {
    "🌿": 2,
    "🍎": 3,
    "🌹": 5,
    "💎": 10,
    "🐍": 20
}


# Создаём взвешенный пул символов.
#
# Например:
# 🌿 встречается 35 раз,
# 🐍 только 7 раз.
SYMBOL_POOL = []

for symbol, weight in SYMBOLS.items():
    SYMBOL_POOL.extend(
        [symbol] * weight
    )


class SlotsView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        bet: int,
        balance_after_bet: int
    ):
        super().__init__(timeout=60)

        self.player_id = player_id
        self.guild_id = guild_id

        # Исходная ставка.
        self.bet = bet

        # Баланс уже после списания ставки.
        self.balance_after_bet = balance_after_bet

        self.finished = False
        self.processing = False

    # =========================================================
    # ГЕНЕРАЦИЯ СИМВОЛОВ
    # =========================================================

    @staticmethod
    def spin() -> tuple[str, str, str]:
        """
        Генерирует три случайных символа
        с учётом их веса.
        """

        return (
            secrets.choice(SYMBOL_POOL),
            secrets.choice(SYMBOL_POOL),
            secrets.choice(SYMBOL_POOL)
        )

    # =========================================================
    # КОЭФФИЦИЕНТ
    # =========================================================

    @staticmethod
    def get_multiplier(
        result: tuple[str, str, str]
    ) -> int:
        """
        Определяет коэффициент выигрыша.

        Пока выигрыш существует только
        при трёх одинаковых символах.
        """

        first, second, third = result

        if first == second == third:
            return PAYOUTS[first]

        return 0

    # =========================================================
    # ОТОБРАЖЕНИЕ
    # =========================================================

    @staticmethod
    def format_result(
        result: tuple[str, str, str]
    ) -> str:
        """
        Например:

        🍎   🌿   💎
        """

        return "   ".join(result)

    # =========================================================
    # ЗАПУСК ИГРЫ
    # =========================================================

    async def play(
        self,
        interaction: discord.Interaction
    ):
        """
        Полный цикл слотов:

        анимация
        ↓
        настоящий результат
        ↓
        выплата
        ↓
        CasinoResultView
        """

        if self.finished or self.processing:
            return

        self.processing = True

        try:
            # =================================================
            # АНИМАЦИЯ
            # =================================================

            for _ in range(3):
                animation_result = self.spin()

                await interaction.edit_original_response(
                    content=(
                        "## 🎰 Слоты\n\n"
                        f"Ваша ставка: "
                        f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                        "### Крутим...\n\n"
                        f"## "
                        f"{self.format_result(animation_result)}"
                    ),
                    view=None
                )

                await asyncio.sleep(0.7)

            # =================================================
            # НАСТОЯЩИЙ РЕЗУЛЬТАТ
            # =================================================

            result = self.spin()

            multiplier = self.get_multiplier(
                result
            )

            self.finished = True

            # =================================================
            # ПРОИГРЫШ
            # =================================================

            if multiplier == 0:
                result_view = CasinoResultView(
                    player_id=self.player_id,
                    guild_id=self.guild_id,
                    game="slots",
                    bet=self.bet
                )

                content = (
                    "## 🎰 Слоты\n\n"
                    f"Ваша ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    f"## "
                    f"{self.format_result(result)}\n\n"
                    "### Проигрыш\n"
                    f"Потеряно: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    f"Баланс: "
                    f"**{self.balance_after_bet} "
                    f"{CURRENCY_SYMBOL}**"
                )

                # Сначала останавливаем старую View.
                self.processing = False
                self.stop()

                # После этого ставим новую ResultView.
                await interaction.edit_original_response(
                    content=content,
                    view=result_view
                )

                return

            # =================================================
            # ПОБЕДА
            # =================================================

            payout_amount = (
                self.bet * multiplier
            )

            new_balance = await payout(
                guild_id=self.guild_id,
                user_id=self.player_id,
                amount=payout_amount,
                game="slots",
                result=(
                    f"win:"
                    f"{result[0]}"
                    f"{result[1]}"
                    f"{result[2]}"
                )
            )

            # Чистая прибыль.
            #
            # Например:
            #
            # ставка 50
            # payout 150
            #
            # прибыль = +100
            profit = (
                payout_amount - self.bet
            )

            result_view = CasinoResultView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                game="slots",
                bet=self.bet
            )

            content = (
                "## 🎰 Слоты\n\n"
                f"Ваша ставка: "
                f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                f"## "
                f"{self.format_result(result)}\n\n"
                "### Победа\n"
                f"Коэффициент: "
                f"**×{multiplier}**\n"
                f"Выигрыш: "
                f"**+{profit} {CURRENCY_SYMBOL}**\n\n"
                f"Баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            )

            self.processing = False
            self.stop()

            await interaction.edit_original_response(
                content=content,
                view=result_view
            )

        except Exception as error:
            self.processing = False

            print(
                "[SLOTS ERROR]",
                type(error).__name__,
                str(error)
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__
            )

            try:
                await interaction.edit_original_response(
                    content=(
                        "## 🎰 Слоты\n\n"
                        "Произошла ошибка во время игры."
                    ),
                    view=None
                )

            except Exception as response_error:
                print(
                    "[SLOTS RESPONSE ERROR]",
                    repr(response_error)
                )