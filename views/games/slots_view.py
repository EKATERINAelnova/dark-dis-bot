import asyncio
import secrets
import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from services.casino import payout
from utils.embeds import (
    casino_embed,
    casino_success_embed,
    casino_warning_embed,
    casino_error_embed,
)

from .result_casino_view import CasinoResultView


# =========================================================
# СИМВОЛЫ
# =========================================================

SYMBOLS = {
    "🌿": 35,
    "🍎": 28,
    "🌹": 18,
    "💎": 12,
    "🐍": 7,
}


PAYOUTS = {
    "🌿": 2,
    "🍎": 3,
    "🌹": 5,
    "💎": 10,
    "🐍": 20,
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
        balance_after_bet: int,
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
            secrets.choice(SYMBOL_POOL),
        )

    # =========================================================
    # КОЭФФИЦИЕНТ
    # =========================================================

    @staticmethod
    def get_multiplier(
        result: tuple[str, str, str],
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
        result: tuple[str, str, str],
    ) -> str:
        """
        Например:

        🍎   🌿   💎
        """

        return "   ".join(result)

    # =========================================================
    # EMBED АНИМАЦИИ
    # =========================================================

    def build_spin_embed(
        self,
        result: tuple[str, str, str],
    ) -> discord.Embed:
        embed = casino_embed(
            title="🎰 СЛОТЫ",
            description=(
                "*Барабаны сада приходят в движение...*"
            ),
        )

        embed.add_field(
            name="🎲 Барабаны",
            value=(
                f"## {self.format_result(result)}"
            ),
            inline=False,
        )

        embed.add_field(
            name="🍎 Ставка",
            value=(
                f"**{self.bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Статус",
            value="`ВРАЩЕНИЕ`",
            inline=True,
        )

        return embed

    # =========================================================
    # EMBED ПРОИГРЫША
    # =========================================================

    def build_loss_embed(
        self,
        result: tuple[str, str, str],
    ) -> discord.Embed:
        embed = casino_warning_embed(
            title="🎰 СЛОТЫ · ПРОИГРЫШ",
            description=(
                "*Символы разошлись. "
                "Ставка остаётся саду.*"
            ),
        )

        embed.add_field(
            name="🎲 Результат",
            value=(
                f"## {self.format_result(result)}"
            ),
            inline=False,
        )

        embed.add_field(
            name="🍎 Ставка",
            value=(
                f"**{self.bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Потеряно",
            value=(
                f"**−{self.bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Баланс после игры",
            value=(
                f"**{self.balance_after_bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=False,
        )

        return embed

    # =========================================================
    # EMBED ПОБЕДЫ
    # =========================================================

    def build_win_embed(
        self,
        result: tuple[str, str, str],
        multiplier: int,
        payout_amount: int,
        profit: int,
        new_balance: int,
    ) -> discord.Embed:
        embed = casino_success_embed(
            title="🎰 СЛОТЫ · ПОБЕДА",
            description=(
                "*Символы сошлись. "
                "Сад отвечает.*"
            ),
        )

        embed.add_field(
            name="✨ Результат",
            value=(
                f"## {self.format_result(result)}"
            ),
            inline=False,
        )

        embed.add_field(
            name="🍎 Ставка",
            value=(
                f"**{self.bet} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Коэффициент",
            value=(
                f"**×{multiplier}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Выплата",
            value=(
                f"**{payout_amount} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Чистый выигрыш",
            value=(
                f"**+{profit} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="Баланс",
            value=(
                f"**{new_balance} "
                f"{CURRENCY_SYMBOL}**"
            ),
            inline=False,
        )

        return embed

    # =========================================================
    # ЗАПУСК ИГРЫ
    # =========================================================

    async def play(
        self,
        interaction: discord.Interaction,
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

                embed = self.build_spin_embed(
                    animation_result
                )

                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
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
                    bet=self.bet,
                )

                embed = self.build_loss_embed(
                    result
                )

                self.processing = False

                # Сначала останавливаем
                # старую игровую View.
                self.stop()

                # Затем устанавливаем ResultView.
                message = (
                    await interaction.edit_original_response(
                        content=None,
                        embed=embed,
                        view=result_view,
                    )
                )

                # Привязываем сообщение,
                # чтобы timeout мог
                # визуально отключить кнопки.
                result_view.bind_message(
                    message
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
                ),
            )

            # Чистая прибыль:
            #
            # ставка 50
            # payout 150
            # profit 100
            profit = (
                payout_amount
                - self.bet
            )

            result_view = CasinoResultView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                game="slots",
                bet=self.bet,
            )

            embed = self.build_win_embed(
                result=result,
                multiplier=multiplier,
                payout_amount=payout_amount,
                profit=profit,
                new_balance=new_balance,
            )

            self.processing = False

            # Останавливаем старую View
            # до установки ResultView.
            self.stop()

            message = (
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=result_view,
                )
            )

            result_view.bind_message(
                message
            )

        # =====================================================
        # ERROR
        # =====================================================

        except Exception as error:
            self.processing = False

            print(
                "[SLOTS ERROR]",
                type(error).__name__,
                str(error),
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__,
            )

            embed = casino_error_embed(
                title="🎰 СЛОТЫ · ОШИБКА",
                description=(
                    "Барабаны остановились раньше времени.\n\n"
                    "Попробуй открыть казино заново."
                ),
            )

            try:
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=None,
                )

            except Exception as response_error:
                print(
                    "[SLOTS RESPONSE ERROR]",
                    repr(response_error),
                )