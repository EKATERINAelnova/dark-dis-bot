import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from database.economy import get_balance
from services.casino import place_bet
from utils.embeds import (
    casino_embed,
    warning_embed,
    error_embed,
)


GAME_NAMES = {
    "roulette": "🎡 Рулетка",
    "slots": "🎰 Слоты",
}


class CasinoResultView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
        game: str,
        bet: int,
    ):
        super().__init__(timeout=180)

        self.player_id = player_id
        self.guild_id = guild_id
        self.game = game
        self.bet = bet

        self.processing = False

        # Сообщение с ResultView.
        # Нужно для timeout и обновления кнопок.
        self.message: (
            discord.InteractionMessage | None
        ) = None

    # =========================================================
    # MESSAGE
    # =========================================================

    def bind_message(
        self,
        message: discord.InteractionMessage,
    ):
        """
        Привязывает Discord-сообщение
        к текущей ResultView.
        """

        self.message = message

    # =========================================================
    # ЗАЩИТА VIEW
    # =========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Не позволяет другим пользователям
        нажимать кнопки чужой партии.
        """

        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая игра",
                description=(
                    "Эта партия принадлежит "
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
    # BUTTONS
    # =========================================================

    def disable_all_buttons(self):
        """
        Отключает все кнопки ResultView.
        """

        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

    # =========================================================
    # ОБЫЧНЫЙ ПЕРЕХОД
    # =========================================================

    async def begin_transition(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Используется для переходов,
        которые точно должны закрыть ResultView:

        - изменить ставку;
        - вернуться в казино.

        Для "Ещё раз" этот метод НЕ используется,
        потому что сначала нужно проверить баланс.
        """

        if self.processing:
            if not interaction.response.is_done():
                embed = warning_embed(
                    title="Действие уже выполняется",
                    description=(
                        "Предыдущий переход "
                        "ещё не завершён."
                    ),
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )

            return False

        self.processing = True

        # Сразу подтверждаем interaction.
        await interaction.response.defer()

        # Отключаем кнопки только после того,
        # как точно решили покинуть ResultView.
        self.disable_all_buttons()

        self.message = (
            await interaction.edit_original_response(
                view=self,
            )
        )

        self.stop()

        return True

    # =========================================================
    # ВЫБОР СТАВКИ
    # =========================================================

    async def open_bet_selection(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ):
        """
        Открывает обычный экран
        выбора новой ставки.

        Используется только тогда,
        когда пользователь сам нажал
        "Изменить ставку".
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
    # НЕДОСТАТОЧНО СРЕДСТВ ДЛЯ ПОВТОРА
    # =========================================================

    async def show_insufficient_replay_balance(
        self,
        interaction: discord.Interaction,
        current_balance: int,
    ):
        """
        Показывает ошибку В ТОМ ЖЕ сообщении.

        ResultView остаётся активной,
        поэтому пользователь может:

        - ещё раз попробовать;
        - изменить ставку;
        - вернуться в казино.
        """

        self.processing = False

        game_name = GAME_NAMES.get(
            self.game,
            "🎰 Казино",
        )

        embed = error_embed(
            title="Недостаточно средств",
            description=(
                f"Не хватает Seeds, чтобы повторить "
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

        self.message = (
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=self,
            )
        )

    # =========================================================
    # ЕЩЁ РАЗ
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
    ):
        """
        Повторяет игру с той же ставкой.

        ВАЖНО:
        сначала проверяется возможность повторить ставку,
        и только после этого ResultView закрывается.
        """

        # =====================================================
        # ЗАЩИТА ОТ ДВОЙНОГО КЛИКА
        # =====================================================

        if self.processing:
            embed = warning_embed(
                title="Действие уже выполняется",
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

        # Подтверждаем interaction,
        # но ResultView пока НЕ закрываем.
        await interaction.response.defer()

        # =====================================================
        # SLOTS
        # =====================================================

        if self.game == "slots":
            from .slots_view import SlotsView

            # В Slots ставка списывается
            # непосредственно перед новой партией.
            #
            # place_bet() атомарно проверяет баланс.
            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="slots",
            )

            # =================================================
            # НЕДОСТАТОЧНО СРЕДСТВ
            # =================================================

            if new_balance is None:
                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id,
                )

                await self.show_insufficient_replay_balance(
                    interaction,
                    current_balance,
                )

                return

            # =================================================
            # СТАВКА УСПЕШНО СПИСАНА
            # =================================================

            # Теперь ResultView действительно
            # можно закрыть.
            self.disable_all_buttons()

            self.message = (
                await interaction.edit_original_response(
                    view=self,
                )
            )

            self.stop()

            slots_view = SlotsView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance,
            )

            await slots_view.play(
                interaction
            )

            return

        # =====================================================
        # ROULETTE
        # =====================================================

        if self.game == "roulette":
            from .roulette_view import RouletteView

            # В рулетке ставка будет списана
            # только после выбора:
            #
            # цвет / чётность / число.
            #
            # Здесь просто проверяем,
            # возможно ли вообще повторить
            # текущий размер ставки.
            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id,
            )

            # =================================================
            # НЕДОСТАТОЧНО СРЕДСТВ
            # =================================================

            if current_balance < self.bet:
                await self.show_insufficient_replay_balance(
                    interaction,
                    current_balance,
                )

                return

            # =================================================
            # ДЕНЕГ ХВАТАЕТ
            # =================================================

            self.disable_all_buttons()

            self.message = (
                await interaction.edit_original_response(
                    view=self,
                )
            )

            self.stop()

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

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=roulette_view,
            )

            return

        # =====================================================
        # НЕИЗВЕСТНАЯ ИГРА
        # =====================================================

        self.processing = False

        raise ValueError(
            f"Неизвестная игра казино: "
            f"{self.game}"
        )

    # =========================================================
    # ИЗМЕНИТЬ СТАВКУ
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
    ):
        """
        Пользователь сам решил
        выбрать другую ставку.
        """

        if not await self.begin_transition(
            interaction
        ):
            return

        current_balance = await get_balance(
            guild_id=self.guild_id,
            user_id=self.player_id,
        )

        await self.open_bet_selection(
            interaction,
            current_balance,
        )

    # =========================================================
    # В КАЗИНО
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
    ):
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

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=casino_view,
        )

    # =========================================================
    # TIMEOUT
    # =========================================================

    async def on_timeout(self):
        """
        После 180 секунд ResultView
        перестаёт быть активной.

        Кнопки визуально отключаются.
        """

        # Если уже выполняется переход,
        # timeout вмешиваться не должен.
        if self.processing:
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

        except discord.Forbidden as error:
            print(
                "[CASINO RESULT TIMEOUT FORBIDDEN]",
                repr(error),
            )

        except discord.HTTPException as error:
            print(
                "[CASINO RESULT TIMEOUT HTTP ERROR]",
                repr(error),
            )

        except Exception as error:
            print(
                "[CASINO RESULT TIMEOUT ERROR]",
                type(error).__name__,
                str(error),
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__,
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
    ):
        """
        Ошибки callback
        не должны исчезать молча.
        """

        self.processing = False

        print(
            "[CASINO RESULT VIEW ERROR]",
            type(error).__name__,
            str(error),
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
        )

        embed = error_embed(
            title="Ошибка казино",
            description=(
                "Во время перехода "
                "произошла ошибка.\n"
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
                "[CASINO RESULT RESPONSE ERROR]",
                repr(response_error),
            )