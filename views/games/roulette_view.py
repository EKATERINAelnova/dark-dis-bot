import secrets

import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import place_bet, payout


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

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "Это не твоя рулетка.",
                ephemeral=True
            )
            return False

        return True

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

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def play(
        self,
        interaction: discord.Interaction,
        choice: str
    ):
        if self.finished:
            await interaction.response.send_message(
                "Эта партия уже завершена.",
                ephemeral=True
            )
            return

        if self.processing:
            await interaction.response.send_message(
                "Колесо уже вращается.",
                ephemeral=True
            )
            return

        # Защита от двух быстрых кликов.
        self.processing = True

        await interaction.response.defer()

        # Только СЕЙЧАС списываем ставку,
        # потому что игрок уже выбрал цвет.
        balance_after_bet = await place_bet(
            guild_id=self.guild_id,
            user_id=self.player_id,
            bet=self.bet,
            game="roulette"
        )

        if balance_after_bet is None:
            self.processing = False

            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id
            )

            await interaction.followup.send(
                (
                    "Недостаточно средств для ставки.\n"
                    f"Баланс: "
                    f"**{current_balance} {CURRENCY_SYMBOL}**"
                ),
                ephemeral=True
            )
            return

        # С этого момента ставка принята.
        self.finished = True

        # Европейская рулетка: 0–36.
        number = secrets.randbelow(37)

        result_color = self.get_color(number)

        won = choice == result_color

        choice_name = self.get_color_name(choice)
        result_name = self.get_color_name(result_color)

        if won:
            # Красное / чёрное дают общую выплату x2.
            #
            # Zero имеет выплату 35:1,
            # поэтому вместе с возвратом ставки x36.
            if choice == "green":
                multiplier = 36
            else:
                multiplier = 2

            payout_amount = self.bet * multiplier

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

            profit = payout_amount - self.bet

            content = (
                "## 🎡 Рулетка\n\n"
                f"Колесо остановилось на "
                f"**{result_name} {number}**\n\n"
                f"Твоя ставка: **{choice_name}**\n"
                f"Размер ставки: "
                f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                "### Победа\n"
                f"Коэффициент: **×{multiplier}**\n"
                f"Выплата: "
                f"**{payout_amount} {CURRENCY_SYMBOL}**\n"
                f"Чистый выигрыш: "
                f"**+{profit} {CURRENCY_SYMBOL}**\n\n"
                f"Баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            )

        else:
            content = (
                "## 🎡 Рулетка\n\n"
                f"Колесо остановилось на "
                f"**{result_name} {number}**\n\n"
                f"Твоя ставка: **{choice_name}**\n"
                f"Размер ставки: "
                f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                "### Проигрыш\n"
                f"Потеряно: "
                f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                f"Баланс: "
                f"**{balance_after_bet} {CURRENCY_SYMBOL}**"
            )

        self.disable_all_buttons()

        await interaction.edit_original_response(
            content=content,
            view=self
        )

        self.processing = False
        self.stop()

    @discord.ui.button(
        label="Красное",
        emoji="🔴",
        style=discord.ButtonStyle.danger
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

    @discord.ui.button(
        label="Чёрное",
        emoji="⚫",
        style=discord.ButtonStyle.secondary
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

    @discord.ui.button(
        label="Zero",
        emoji="🟢",
        style=discord.ButtonStyle.success
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