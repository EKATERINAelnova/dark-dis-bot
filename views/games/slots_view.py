import asyncio
import secrets

import discord

from config.economy import CURRENCY_SYMBOL
from services.casino import payout


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
        self.bet = bet
        self.balance_after_bet = balance_after_bet

        self.finished = False

    @staticmethod
    def spin() -> tuple[str, str, str]:
        """
        Генерирует итоговые три символа.
        """

        return (
            secrets.choice(SYMBOL_POOL),
            secrets.choice(SYMBOL_POOL),
            secrets.choice(SYMBOL_POOL)
        )

    @staticmethod
    def get_multiplier(
        result: tuple[str, str, str]
    ) -> int:
        """
        Определяет коэффициент выигрыша.
        """

        first, second, third = result

        if first == second == third:
            return PAYOUTS[first]

        return 0

    @staticmethod
    def format_result(
        result: tuple[str, str, str]
    ) -> str:
        return "   ".join(result)

    async def play(
        self,
        interaction: discord.Interaction
    ):
        """
        Запускает слот:
        анимация → результат → выплата.
        """

        if self.finished:
            return

        # -------------------------
        # АНИМАЦИЯ
        # -------------------------

        for _ in range(3):
            animation_result = self.spin()

            await interaction.edit_original_response(
                content=(
                    "## 🎰 Слоты\n\n"
                    f"Ваша ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    "### Крутим...\n\n"
                    f"## {self.format_result(animation_result)}"
                ),
                view=None
            )

            await asyncio.sleep(0.7)

        # -------------------------
        # НАСТОЯЩИЙ РЕЗУЛЬТАТ
        # -------------------------

        result = self.spin()

        multiplier = self.get_multiplier(
            result
        )

        self.finished = True

        # -------------------------
        # ПРОИГРЫШ
        # -------------------------

        if multiplier == 0:
            await interaction.edit_original_response(
                content=(
                    "## 🎰 Слоты\n\n"
                    f"Ваша ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    f"## {self.format_result(result)}\n\n"
                    "### Проигрыш\n"
                    f"Потеряно: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    f"Баланс: "
                    f"**{self.balance_after_bet} "
                    f"{CURRENCY_SYMBOL}**"
                ),
                view=None
            )

            self.stop()
            return

        # -------------------------
        # ПОБЕДА
        # -------------------------

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

        profit = (
            payout_amount - self.bet
        )

        await interaction.edit_original_response(
            content=(
                "## 🎰 Слоты\n\n"
                f"Ваша ставка: "
                f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                f"## {self.format_result(result)}\n\n"
                "### Победа\n"
                f"Коэффициент: **×{multiplier}**\n"
                f"Выигрыш: "
                f"**+{profit} {CURRENCY_SYMBOL}**\n\n"
                f"Баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            ),
            view=None
        )

        self.stop()