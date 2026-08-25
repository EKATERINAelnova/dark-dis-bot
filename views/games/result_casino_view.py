import logging

import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import place_bet

from utils.embeds import (
    casino_embed,
    warning_embed,
    error_embed,
)


logger = logging.getLogger(
    "lost_eden.casino.result"
)


GAME_NAMES = {
    "roulette": "🎡 Рулетка",
    "slots": "🎰 Слоты",
}


class CasinoResultView(
    discord.ui.View
):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        game: str,
        bet: int,
    ):
        super().__init__(
            timeout=180
        )

        self.player_id = player_id
        self.guild_id = guild_id
        self.game = game
        self.bet = bet

        self.processing = False

        self.message: (
            discord.InteractionMessage
            | None
        ) = None

    # =========================================================
    # MESSAGE
    # =========================================================

    def bind_message(
        self,
        message: discord.InteractionMessage,
    ) -> None:
        """
        Привязывает сообщение Discord
        к ResultView.

        Используется для timeout.
        """

        self.message = message

    # =========================================================
    # INTERACTION CHECK
    # =========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Не позволяет другому пользователю
        управлять чужой игрой.
        """

        if (
            interaction.user.id
            == self.player_id
        ):
            return True

        embed = error_embed(
            title="Чужая игра",
            description=(
                "Эта партия принадлежит "
                "другому игроку."
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

        except discord.HTTPException:
            logger.exception(
                (
                    "Не удалось отправить сообщение "
                    "о чужой игре | "
                    "guild=%s | owner=%s | user=%s"
                ),
                self.guild_id,
                self.player_id,
                interaction.user.id,
            )

        return False

    # =========================================================
    # BUTTONS
    # =========================================================

    def disable_all_buttons(
        self,
    ) -> None:
        """
        Отключает все кнопки View.
        """

        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

    # =========================================================
    # PROCESSING WARNING
    # =========================================================

    async def send_processing_warning(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """
        Сообщает пользователю,
        что предыдущий переход
        ещё выполняется.
        """

        embed = warning_embed(
            title="Действие уже выполняется",
            description=(
                "Предыдущий переход "
                "ещё не завершён."
            ),
        )

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

    # =========================================================
    # TRANSITION
    # =========================================================

    async def begin_transition(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Начинает переход между экранами.

        ВАЖНО:
        текущая View здесь ещё НЕ выключается
        и НЕ останавливается.

        Она закрывается только после того,
        как новый экран успешно создан.
        """

        if self.processing:
            await self.send_processing_warning(
                interaction
            )

            return False

        self.processing = True

        if not interaction.response.is_done():
            await interaction.response.defer()

        return True

    def finish_transition(
        self,
    ) -> None:
        """
        Завершает успешный переход.

        Старую ResultView после этого
        больше нельзя использовать.
        """

        self.disable_all_buttons()
        self.stop()

    # =========================================================
    # BET SELECTION
    # =========================================================

    async def open_bet_selection(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ) -> None:
        """
        Открывает выбор новой ставки.
        """

        from ..bet_view import BetView

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
                "Выбери новую ставку."
            ),
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=bet_view,
        )

    # =========================================================
    # INSUFFICIENT BALANCE
    # =========================================================

    async def show_insufficient_replay_balance(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ) -> None:
        """
        Показывает недостаток средств,
        не закрывая текущую ResultView.

        Пользователь после этого всё ещё
        может изменить ставку или
        вернуться в казино.
        """

        game_name = GAME_NAMES.get(
            self.game,
            "🎰 Казино",
        )

        embed = error_embed(
            title="Недостаточно средств",
            description=(
                "Недостаточно средств, "
                "чтобы повторить "
                f"партию в **{game_name}**.\n\n"

                f"Ставка: "
                f"**{self.bet} "
                f"{CURRENCY_SYMBOL}**\n"

                f"Твой баланс: "
                f"**{current_balance} "
                f"{CURRENCY_SYMBOL}**\n\n"

                "Измени ставку "
                "или вернись в казино."
            ),
        )

        try:
            self.message = (
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=self,
                )
            )

        finally:
            # Разрешаем нажимать кнопки
            # снова только после завершения
            # обновления сообщения.
            self.processing = False

    # =========================================================
    # PLAY AGAIN
    # =========================================================

    @discord.ui.button(
        label="Ещё раз",
        emoji="🔁",
        style=discord.ButtonStyle.success,
        custom_id="casino_play_again",
    )
    async def play_again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """
        Повторяет игру с той же ставкой.

        ResultView остаётся активной,
        пока новый экран игры
        не будет успешно подготовлен.
        """

        if not await self.begin_transition(
            interaction
        ):
            return

        # =====================================================
        # SLOTS
        # =====================================================

        if self.game == "slots":
            from .slots_view import SlotsView

            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="slots",
            )

            # =================================================
            # INSUFFICIENT BALANCE
            # =================================================

            if new_balance is None:
                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                await self.show_insufficient_replay_balance(
                    interaction=interaction,
                    current_balance=current_balance,
                )

                return

            # =================================================
            # NEW GAME
            # =================================================

            slots_view = SlotsView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance,
            )

            # SlotsView сама заменяет текущий
            # экран через interaction.
            #
            # Старую ResultView останавливаем
            # только после успешного запуска.
            await slots_view.play(
                interaction
            )

            self.finish_transition()

            return

        # =====================================================
        # ROULETTE
        # =====================================================

        if self.game == "roulette":
            from .roulette_view import RouletteView

            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id,
            )

            # =================================================
            # INSUFFICIENT BALANCE
            # =================================================

            if current_balance < self.bet:
                await self.show_insufficient_replay_balance(
                    interaction=interaction,
                    current_balance=current_balance,
                )

                return

            # =================================================
            # NEW ROULETTE SCREEN
            # =================================================

            roulette_view = RouletteView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
            )

            embed = casino_embed(
                title="🎡 РУЛЕТКА",
                description=(
                    "*Колесо ждёт новой ставки.*\n\n"

                    f"Ставка: "
                    f"**{self.bet} "
                    f"{CURRENCY_SYMBOL}**\n\n"

                    "Выбери цвет, чётность "
                    "или точное число."
                ),
            )

            self.message = (
                await interaction.edit_original_response(
                    content=None,
                    embed=embed,
                    view=roulette_view,
                )
            )

            self.finish_transition()

            return

        # =====================================================
        # UNKNOWN GAME
        # =====================================================

        self.processing = False

        raise ValueError(
            "Неизвестная игра казино: "
            f"{self.game}"
        )

    # =========================================================
    # CHANGE BET
    # =========================================================

    @discord.ui.button(
        label="Изменить ставку",
        emoji="💰",
        style=discord.ButtonStyle.primary,
        custom_id="casino_change_bet",
    )
    async def change_bet(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """
        Открывает выбор другой ставки.
        """

        if not await self.begin_transition(
            interaction
        ):
            return

        # Сначала получаем данные.
        #
        # Если БД даст ошибку,
        # старая ResultView ещё останется живой.
        current_balance = await get_balance(
            guild_id=self.guild_id,
            user_id=self.player_id,
        )

        await self.open_bet_selection(
            interaction=interaction,
            current_balance=current_balance,
        )

        self.finish_transition()

    # =========================================================
    # BACK TO CASINO
    # =========================================================

    @discord.ui.button(
        label="В казино",
        emoji="🎰",
        style=discord.ButtonStyle.secondary,
        custom_id="casino_back",
    )
    async def back_to_casino(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        """
        Возвращает пользователя
        к выбору игры.
        """

        if not await self.begin_transition(
            interaction
        ):
            return

        from ..casino_view import CasinoView

        casino_view = CasinoView(
            self.player_id
        )

        embed = casino_embed(
            title="🎰 LOST EDEN CASINO",
            description=(
                "Добро пожаловать "
                "за столы сада.\n\n"
                "Выбери игру:"
            ),
        )

        self.message = (
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=casino_view,
            )
        )

        self.finish_transition()

    # =========================================================
    # TIMEOUT
    # =========================================================

    async def on_timeout(
        self,
    ) -> None:
        """
        После timeout результат остаётся
        на экране, но кнопки отключаются.
        """

        if self.processing:
            logger.debug(
                (
                    "Timeout пропущен: "
                    "выполняется переход | "
                    "guild=%s | user=%s | game=%s"
                ),
                self.guild_id,
                self.player_id,
                self.game,
            )

            return

        self.processing = True

        self.disable_all_buttons()

        if self.message is None:
            self.stop()
            return

        try:
            await self.message.edit(
                view=self,
            )

        except discord.NotFound:
            # Сообщение уже удалено.
            pass

        except discord.Forbidden:
            logger.warning(
                (
                    "Нет прав на изменение "
                    "ResultView после timeout | "
                    "guild=%s | user=%s | game=%s"
                ),
                self.guild_id,
                self.player_id,
                self.game,
            )

        except discord.HTTPException as error:
            logger.warning(
                (
                    "Ошибка Discord API "
                    "при timeout ResultView | "
                    "guild=%s | "
                    "user=%s | "
                    "game=%s | "
                    "status=%s | "
                    "error=%s"
                ),
                self.guild_id,
                self.player_id,
                self.game,
                error.status,
                error,
            )

        except Exception:
            logger.exception(
                (
                    "Неожиданная ошибка "
                    "ResultView timeout | "
                    "guild=%s | user=%s | game=%s"
                ),
                self.guild_id,
                self.player_id,
                self.game,
            )

        finally:
            self.stop()

    # =========================================================
    # ERROR
    # =========================================================

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        """
        Общая обработка ошибок callback
        этой View.
        """

        self.processing = False

        logger.error(
            (
                "Ошибка CasinoResultView | "
                "guild=%s | "
                "user=%s | "
                "game=%s | "
                "item=%s"
            ),
            self.guild_id,
            self.player_id,
            self.game,
            type(item).__name__,
            exc_info=(
                type(error),
                error,
                error.__traceback__,
            ),
        )

        embed = error_embed(
            title="Ошибка казино",
            description=(
                "Во время перехода "
                "произошла ошибка.\n"
                "Попробуй ещё раз "
                "или открой казино заново."
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

        except discord.HTTPException:
            logger.exception(
                (
                    "Не удалось отправить "
                    "сообщение об ошибке "
                    "CasinoResultView | "
                    "guild=%s | user=%s | game=%s"
                ),
                self.guild_id,
                self.player_id,
                self.game,
            )