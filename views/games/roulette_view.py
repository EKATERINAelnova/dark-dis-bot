import secrets
import traceback

import discord

from config.economy import (
    CURRENCY_SYMBOL,
    CASINO_MIN_BET,
)
from database.economy import get_balance
from services.casino import (
    place_bet,
    payout,
)
from utils.embeds import (
    casino_success_embed,
    casino_warning_embed,
    casino_error_embed,
)

from .result_casino_view import CasinoResultView


# =========================================================
# ЕВРОПЕЙСКАЯ РУЛЕТКА
# =========================================================

RED_NUMBERS = {
    1, 3, 5, 7, 9,
    12, 14, 16, 18,
    19, 21, 23, 25, 27,
    30, 32, 34, 36,
}


# =========================================================
# ОТОБРАЖЕНИЕ ЧИСЕЛ
# =========================================================

def get_number_emoji(
    number: int,
) -> str:
    if number == 0:
        return "🟢"

    if number in RED_NUMBERS:
        return "🔴"

    return "⚫"


def format_number(
    number: int,
) -> str:
    return (
        f"{get_number_emoji(number)} "
        f"{number}"
    )


# =========================================================
# OPTIONS ДЛЯ SELECT
# =========================================================

NUMBER_OPTIONS_LOW = [
    discord.SelectOption(
        label=str(number),
        value=str(number),
        emoji=get_number_emoji(number),
    )
    for number in range(1, 19)
]


NUMBER_OPTIONS_HIGH = [
    discord.SelectOption(
        label=str(number),
        value=str(number),
        emoji=get_number_emoji(number),
    )
    for number in range(19, 37)
]


class RouletteView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        bet: int,
    ):
        super().__init__(
            timeout=60
        )

        self.player_id = player_id
        self.guild_id = guild_id
        self.bet = bet

        self.processing = False
        self.finished = False

    # =========================================================
    # ЗАЩИТА VIEW
    # =========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.player_id:
            embed = casino_error_embed(
                title="🎡 ЧУЖАЯ РУЛЕТКА",
                description=(
                    "Это колесо принадлежит "
                    "другому игроку."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return False

        return True

    # =========================================================
    # ЦВЕТ ЧИСЛА
    # =========================================================

    @staticmethod
    def get_color(
        number: int,
    ) -> str:
        if number == 0:
            return "green"

        if number in RED_NUMBERS:
            return "red"

        return "black"

    # =========================================================
    # ЧЁТНОСТЬ
    # =========================================================

    @staticmethod
    def get_parity(
        number: int,
    ) -> str | None:
        """
        Zero не является ни чётным,
        ни нечётным в рулетке.
        """

        if number == 0:
            return None

        if number % 2 == 0:
            return "even"

        return "odd"

    # =========================================================
    # НАЗВАНИЕ СТАВКИ
    # =========================================================

    @staticmethod
    def get_bet_name(
        bet_type: str,
        bet_value: str | int,
    ) -> str:
        if bet_type == "color":
            names = {
                "red": "🔴 Красное",
                "black": "⚫ Чёрное",
            }

            return names[str(bet_value)]

        if bet_type == "parity":
            names = {
                "even": "🔢 Чётное",
                "odd": "🔢 Нечётное",
            }

            return names[str(bet_value)]

        if bet_type == "number":
            number = int(
                bet_value
            )

            return (
                "🎯 Точное число "
                f"{format_number(number)}"
            )

        raise ValueError(
            f"Неизвестный тип ставки: "
            f"{bet_type}"
        )

    # =========================================================
    # ПРОВЕРКА ВЫИГРЫША
    # =========================================================

    @classmethod
    def check_win(
        cls,
        number: int,
        bet_type: str,
        bet_value: str | int,
    ) -> bool:
        # =====================================================
        # ЦВЕТ
        # =====================================================

        if bet_type == "color":
            return (
                cls.get_color(number)
                == str(bet_value)
            )

        # =====================================================
        # ЧЁТ / НЕЧЁТ
        # =====================================================

        if bet_type == "parity":
            return (
                cls.get_parity(number)
                == str(bet_value)
            )

        # =====================================================
        # ТОЧНОЕ ЧИСЛО
        # =====================================================

        if bet_type == "number":
            return (
                number
                == int(bet_value)
            )

        raise ValueError(
            f"Неизвестный тип ставки: "
            f"{bet_type}"
        )

    # =========================================================
    # КОЭФФИЦИЕНТ
    # =========================================================

    @staticmethod
    def get_multiplier(
        bet_type: str,
    ) -> int:
        # Точное число:
        # прибыль 35:1,
        # общая выплата ×36.
        if bet_type == "number":
            return 36

        # Цвет / чётность:
        # прибыль 1:1,
        # общая выплата ×2.
        if bet_type in {
            "color",
            "parity",
        }:
            return 2

        raise ValueError(
            f"Неизвестный тип ставки: "
            f"{bet_type}"
        )

    # =========================================================
    # COMPONENTS
    # =========================================================

    def disable_all_components(
        self,
    ):
        """
        Отключает и кнопки,
        и Select после выбора ставки.
        """

        for item in self.children:
            if isinstance(
                item,
                (
                    discord.ui.Button,
                    discord.ui.Select,
                ),
            ):
                item.disabled = True

    # =========================================================
    # НЕДОСТАТОЧНО СРЕДСТВ
    # =========================================================

    async def show_insufficient_balance(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ):
        from ..bet_view import BetView

        # =====================================================
        # НИЖЕ МИНИМАЛЬНОЙ СТАВКИ
        # =====================================================

        if current_balance < CASINO_MIN_BET:
            embed = casino_error_embed(
                title="🎡 НЕДОСТАТОЧНО СРЕДСТВ",
                description=(
                    "Колесо не примет ставку.\n\n"
                    f"Выбранная ставка: "
                    f"**{self.bet} "
                    f"{CURRENCY_SYMBOL}**\n"
                    f"Твой баланс: "
                    f"**{current_balance} "
                    f"{CURRENCY_SYMBOL}**\n"
                    f"Минимальная ставка: "
                    f"**{CASINO_MIN_BET} "
                    f"{CURRENCY_SYMBOL}**"
                ),
            )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None,
            )

            return

        # =====================================================
        # МОЖНО УМЕНЬШИТЬ СТАВКУ
        # =====================================================

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game="roulette",
            balance=current_balance,
        )

        embed = casino_error_embed(
            title="🎡 НЕДОСТАТОЧНО СРЕДСТВ",
            description=(
                "Баланс изменился после "
                "выбора ставки.\n\n"
                f"Выбранная ставка: "
                f"**{self.bet} "
                f"{CURRENCY_SYMBOL}**\n"
                f"Твой баланс: "
                f"**{current_balance} "
                f"{CURRENCY_SYMBOL}**\n\n"
                "Выбери меньшую ставку."
            ),
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=bet_view,
        )

    # =========================================================
    # ОСНОВНАЯ ИГРА
    # =========================================================

    async def play(
        self,
        interaction: discord.Interaction,
        bet_type: str,
        bet_value: str | int,
    ):
        # =====================================================
        # ПАРТИЯ ЗАКОНЧЕНА
        # =====================================================

        if self.finished:
            embed = casino_warning_embed(
                title="🎡 ПАРТИЯ ЗАВЕРШЕНА",
                description=(
                    "Это колесо уже остановилось."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        # =====================================================
        # УЖЕ ВРАЩАЕТСЯ
        # =====================================================

        if self.processing:
            embed = casino_warning_embed(
                title="🎡 КОЛЕСО УЖЕ ВРАЩАЕТСЯ",
                description=(
                    "Дождись результата "
                    "текущего вращения."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        self.processing = True

        try:
            # =================================================
            # ВАЛИДАЦИЯ СТАВКИ
            # =================================================

            if bet_type == "color":
                if bet_value not in {
                    "red",
                    "black",
                }:
                    raise ValueError(
                        "Некорректный цвет"
                    )

            elif bet_type == "parity":
                if bet_value not in {
                    "even",
                    "odd",
                }:
                    raise ValueError(
                        "Некорректная чётность"
                    )

            elif bet_type == "number":
                number_choice = int(
                    bet_value
                )

                if not 0 <= number_choice <= 36:
                    raise ValueError(
                        "Некорректное число"
                    )

            else:
                raise ValueError(
                    "Неизвестный тип ставки"
                )

            # =================================================
            # ACK
            # =================================================

            await interaction.response.defer()

            # Сразу блокируем UI.
            self.disable_all_components()

            await interaction.edit_original_response(
                view=self,
            )

            # =================================================
            # СПИСЫВАЕМ СТАВКУ
            # =================================================

            balance_after_bet = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="roulette",
            )

            if balance_after_bet is None:
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

            self.finished = True

            # =================================================
            # КРУТИМ КОЛЕСО
            # =================================================

            number = secrets.randbelow(
                37
            )

            won = self.check_win(
                number=number,
                bet_type=bet_type,
                bet_value=bet_value,
            )

            bet_name = self.get_bet_name(
                bet_type=bet_type,
                bet_value=bet_value,
            )

            multiplier = self.get_multiplier(
                bet_type
            )

            result_number = format_number(
                number
            )

            # =================================================
            # ПОБЕДА
            # =================================================

            if won:
                payout_amount = (
                    self.bet
                    * multiplier
                )

                new_balance = await payout(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                    amount=payout_amount,
                    game="roulette",
                    result=(
                        f"win:"
                        f"{bet_type}:"
                        f"{bet_value}:"
                        f"number={number}"
                    ),
                )

                profit = (
                    payout_amount
                    - self.bet
                )

                embed = casino_success_embed(
                    title="🎡 РУЛЕТКА · ПОБЕДА",
                    description=(
                        "*Колесо остановилось. "
                        "Сад сделал свой выбор.*\n\n"
                        f"## {result_number}"
                    ),
                )

                embed.add_field(
                    name="🎯 Твоя ставка",
                    value=(
                        f"{bet_name}\n"
                        f"**{self.bet} "
                        f"{CURRENCY_SYMBOL}**"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="✨ Коэффициент",
                    value=(
                        f"**×{multiplier}**"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="\u200b",
                    value="\u200b",
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
                    inline=True,
                )

            # =================================================
            # ПРОИГРЫШ
            # =================================================

            else:
                embed = casino_warning_embed(
                    title="🎡 РУЛЕТКА · ПРОИГРЫШ",
                    description=(
                        "*Колесо остановилось. "
                        "На этот раз сад "
                        "забирает ставку.*\n\n"
                        f"## {result_number}"
                    ),
                )

                embed.add_field(
                    name="🎯 Твоя ставка",
                    value=(
                        f"{bet_name}\n"
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
                    name="\u200b",
                    value="\u200b",
                    inline=True,
                )

                embed.add_field(
                    name="Баланс после игры",
                    value=(
                        f"**{balance_after_bet} "
                        f"{CURRENCY_SYMBOL}**"
                    ),
                    inline=False,
                )

            # =================================================
            # RESULT VIEW
            # =================================================

            result_view = CasinoResultView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                game="roulette",
                bet=self.bet,
            )

            self.processing = False

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
                "[ROULETTE ERROR]",
                type(error).__name__,
                str(error),
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__,
            )

            embed = casino_error_embed(
                title="🎡 РУЛЕТКА · ОШИБКА",
                description=(
                    "Колесо остановилось "
                    "раньше времени.\n\n"
                    "Попробуй открыть казино заново."
                ),
            )

            try:
                if interaction.response.is_done():
                    await interaction.edit_original_response(
                        content=None,
                        embed=embed,
                        view=None,
                    )

                else:
                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )

            except Exception as response_error:
                print(
                    "[ROULETTE RESPONSE ERROR]",
                    repr(response_error),
                )

    # =========================================================
    # КРАСНОЕ
    # =========================================================

    @discord.ui.button(
        label="Красное",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="roulette_red",
        row=0,
    )
    async def red(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.play(
            interaction,
            bet_type="color",
            bet_value="red",
        )

    # =========================================================
    # ЧЁРНОЕ
    # =========================================================

    @discord.ui.button(
        label="Чёрное",
        emoji="⚫",
        style=discord.ButtonStyle.secondary,
        custom_id="roulette_black",
        row=0,
    )
    async def black(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.play(
            interaction,
            bet_type="color",
            bet_value="black",
        )

    # =========================================================
    # ЧЁТНОЕ
    # =========================================================

    @discord.ui.button(
        label="Чётное",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_even",
        row=0,
    )
    async def even(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.play(
            interaction,
            bet_type="parity",
            bet_value="even",
        )

    # =========================================================
    # НЕЧЁТНОЕ
    # =========================================================

    @discord.ui.button(
        label="Нечётное",
        style=discord.ButtonStyle.primary,
        custom_id="roulette_odd",
        row=0,
    )
    async def odd(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.play(
            interaction,
            bet_type="parity",
            bet_value="odd",
        )

    # =========================================================
    # ZERO
    # =========================================================

    @discord.ui.button(
        label="Zero",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="roulette_zero",
        row=0,
    )
    async def zero(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.play(
            interaction,
            bet_type="number",
            bet_value=0,
        )

    # =========================================================
    # ЧИСЛА 1–18
    # =========================================================

    @discord.ui.select(
        placeholder="🎯 Точное число · 1–18",
        min_values=1,
        max_values=1,
        options=NUMBER_OPTIONS_LOW,
        custom_id="roulette_numbers_low",
        row=1,
    )
    async def numbers_low(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ):
        number = int(
            select.values[0]
        )

        await self.play(
            interaction,
            bet_type="number",
            bet_value=number,
        )

    # =========================================================
    # ЧИСЛА 19–36
    # =========================================================

    @discord.ui.select(
        placeholder="🎯 Точное число · 19–36",
        min_values=1,
        max_values=1,
        options=NUMBER_OPTIONS_HIGH,
        custom_id="roulette_numbers_high",
        row=2,
    )
    async def numbers_high(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ):
        number = int(
            select.values[0]
        )

        await self.play(
            interaction,
            bet_type="number",
            bet_value=number,
        )