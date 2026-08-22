import secrets
import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import place_bet, payout
from .result_casino_view import CasinoResultView
from utils.embeds import (
    success_embed,
    warning_embed,
    error_embed,
)

RED_NUMBERS = {
    1, 3, 5, 7, 9,
    12, 14, 16, 18,
    19, 21, 23, 25, 27,
    30, 32, 34, 36
}


class RouletteView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        bet: int
    ):
        super().__init__(timeout=60)

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
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая рулетка",
                description="Это колесо принадлежит другому игроку.",
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
    def get_color(number: int) -> str:
        if number == 0:
            return "green"

        if number in RED_NUMBERS:
            return "red"

        return "black"

    @staticmethod
    def get_color_name(color: str) -> str:
        names = {
            "red": "🔴 Красное",
            "black": "⚫ Чёрное",
            "green": "🟢 Zero"
        }

        return names[color]

    # =========================================================
    # КНОПКИ
    # =========================================================

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    # =========================================================
    # ИГРА
    # =========================================================

    async def play(
        self,
        interaction: discord.Interaction,
        choice: str
    ):
        if self.finished:
            embed = warning_embed(
                title="Партия завершена",
                description="Это колесо уже остановилось.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        if self.processing:
            embed = warning_embed(
                title="Колесо уже вращается",
                description="Дождись результата текущего вращения.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return

        self.processing = True

        try:
            # Сразу подтверждаем interaction.
            await interaction.response.defer()

            # =================================================
            # СПИСЫВАЕМ СТАВКУ
            # =================================================

            # В рулетке ставка списывается
            # только после выбора цвета.
            balance_after_bet = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="roulette"
            )

            # Баланс мог измениться с момента
            # выбора размера ставки.
            if balance_after_bet is None:
                self.processing = False

                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id
                )

                embed = error_embed(
                    title="Недостаточно средств",
                    description=(
                        "Баланс изменился после выбора ставки.\n\n"
                        f"Баланс: "
                        f"**{current_balance} {CURRENCY_SYMBOL}**"
                    ),
                )

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True,
                )

                return

            # После успешного списания
            # повторно играть этой View уже нельзя.
            self.finished = True

            # =================================================
            # КРУТИМ РУЛЕТКУ
            # =================================================

            # Европейская рулетка:
            # числа от 0 до 36.
            number = secrets.randbelow(37)

            result_color = self.get_color(
                number
            )

            won = (
                choice == result_color
            )

            choice_name = self.get_color_name(
                choice
            )

            result_name = self.get_color_name(
                result_color
            )

            # =================================================
            # ПОБЕДА
            # =================================================

            if won:
                # Красное / чёрное:
                # полная выплата x2.
                #
                # Zero:
                # прибыль 35:1,
                # полная выплата x36.
                if choice == "green":
                    multiplier = 36
                else:
                    multiplier = 2

                payout_amount = (
                    self.bet * multiplier
                )

                new_balance = await payout(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                    amount=payout_amount,
                    game="roulette",
                    result=(
                        f"win:"
                        f"{choice}:"
                        f"number={number}"
                    )
                )

                profit = (
                    payout_amount - self.bet
                )

                embed = success_embed(
                    title="🎡 Рулетка · Победа",
                    description=(
                        f"Колесо остановилось на "
                        f"**{result_name} {number}**"
                    ),
                )

                embed.add_field(
                    name="Ставка",
                    value=(
                        f"{choice_name}\n"
                        f"**{self.bet} {CURRENCY_SYMBOL}**"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="Коэффициент",
                    value=f"**×{multiplier}**",
                    inline=True,
                )

                embed.add_field(
                    name="Итог",
                    value=(
                        f"Выплата: "
                        f"**{payout_amount} {CURRENCY_SYMBOL}**\n"
                        f"Чистый выигрыш: "
                        f"**+{profit} {CURRENCY_SYMBOL}**\n"
                        f"Баланс: "
                        f"**{new_balance} {CURRENCY_SYMBOL}**"
                    ),
                    inline=False,
                )

            # =================================================
            # ПРОИГРЫШ
            # =================================================

            else:
                embed = warning_embed(
                    title="🎡 Рулетка · Проигрыш",
                    description=(
                        f"Колесо остановилось на "
                        f"**{result_name} {number}**"
                    ),
                )

                embed.add_field(
                    name="Ставка",
                    value=(
                        f"{choice_name}\n"
                        f"**{self.bet} {CURRENCY_SYMBOL}**"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="Итог",
                    value=(
                        f"Потеряно: "
                        f"**{self.bet} {CURRENCY_SYMBOL}**\n"
                        f"Баланс: "
                        f"**{balance_after_bet} {CURRENCY_SYMBOL}**"
                    ),
                    inline=False,
                )

            # =================================================
            # ЭКРАН ПОСЛЕ ИГРЫ
            # =================================================

            result_view = CasinoResultView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                game="roulette",
                bet=self.bet
            )

            self.processing = False

            # Сначала останавливаем RouletteView.
            self.stop()

            # Только потом устанавливаем новую View.
            message = await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=result_view,
            )

            result_view.bind_message(message)

        except Exception as error:
            self.processing = False

            print(
                "[ROULETTE ERROR]",
                type(error).__name__,
                str(error)
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__
            )

            embed = error_embed(
                title="Ошибка рулетки",
                description=(
                    "Во время вращения произошла ошибка.\n"
                    "Попробуй открыть казино заново."
                ),
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        embed=embed,
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )

            except Exception as response_error:
                print(
                    "[ROULETTE RESPONSE ERROR]",
                    repr(response_error)
                )

    # =========================================================
    # КРАСНОЕ
    # =========================================================

    @discord.ui.button(
        label="Красное",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="roulette_red"
    )
    async def red(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.play(
            interaction,
            "red"
        )

    # =========================================================
    # ЧЁРНОЕ
    # =========================================================

    @discord.ui.button(
        label="Чёрное",
        emoji="⚫",
        style=discord.ButtonStyle.secondary,
        custom_id="roulette_black"
    )
    async def black(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.play(
            interaction,
            "black"
        )

    # =========================================================
    # ZERO
    # =========================================================

    @discord.ui.button(
        label="Zero",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="roulette_green"
    )
    async def green(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.play(
            interaction,
            "green"
        )