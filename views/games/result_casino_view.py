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
        bet: int
    ):
        super().__init__(timeout=180)

        self.player_id = player_id
        self.guild_id = guild_id
        self.game = game
        self.bet = bet

        self.processing = False

        # Сохраняем сообщение, к которому привязана View.
        # Нужно для визуального отключения кнопок по timeout.
        self.message: discord.InteractionMessage | None = None

    # =========================================================
    # СООБЩЕНИЕ
    # =========================================================

    def bind_message(
        self,
        message: discord.InteractionMessage
    ):
        """
        Сохраняет сообщение, на котором находится ResultView.

        Нужно для on_timeout().
        """

        self.message = message

    # =========================================================
    # ЗАЩИТА VIEW
    # =========================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Не позволяет другим пользователям
        нажимать кнопки чужой игры.
        """

        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая игра",
                description="Эта партия принадлежит другому игроку.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
            return False

        return True

    # =========================================================
    # КНОПКИ
    # =========================================================

    def disable_all_buttons(self):
        """
        Выключает все кнопки ResultView.
        """

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    # =========================================================
    # ПЕРЕХОД
    # =========================================================

    async def begin_transition(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Безопасно начинает переход
        с ResultView на другой экран.

        Порядок важен:

        1. подтверждаем interaction;
        2. выключаем текущие кнопки;
        3. обновляем сообщение;
        4. останавливаем старую View;
        5. callback устанавливает новую View.
        """

        if self.processing:
            if not interaction.response.is_done():
                embed = warning_embed(
                    title="Действие уже выполняется",
                    description="Предыдущий переход ещё не завершён.",
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )

            return False

        self.processing = True

        # Сразу отвечаем Discord,
        # чтобы interaction не протух.
        await interaction.response.defer()

        # Визуально отключаем старые кнопки.
        self.disable_all_buttons()

        self.message = await interaction.edit_original_response(
            view=self
        )

        # Критично:
        # старая View должна быть остановлена
        # до установки новой.
        self.stop()

        return True

    # =========================================================
    # ВЫБОР СТАВКИ
    # =========================================================

    async def open_bet_selection(
        self,
        interaction: discord.Interaction,
        current_balance: int
    ):
        """
        Возвращает пользователя
        к выбору ставки текущей игры.
        """

        from ..bet_view import BetView

        bet_view = BetView(
            player_id=self.player_id,
            guild_id=self.guild_id,
            game=self.game,
            balance=current_balance
        )

        game_name = GAME_NAMES[self.game]

        embed = casino_embed(
            title=game_name,
            description=(
                f"Баланс: "
                f"**{current_balance} {CURRENCY_SYMBOL}**\n\n"
                "Выбери ставку:"
            ),
        )

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=bet_view,
        )

    # =========================================================
    # ЕЩЁ РАЗ
    # =========================================================

    @discord.ui.button(
        label="Ещё раз",
        emoji="🔁",
        style=discord.ButtonStyle.success,
        custom_id="casino_play_again"
    )
    async def play_again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.begin_transition(
            interaction
        ):
            return

        # =====================================================
        # SLOTS
        # =====================================================

        if self.game == "slots":
            from .slots_view import SlotsView

            # Слоты запускаются сразу,
            # поэтому ставку списываем здесь.
            new_balance = await place_bet(
                guild_id=self.guild_id,
                user_id=self.player_id,
                bet=self.bet,
                game="slots"
            )

            # Баланса на предыдущую ставку
            # больше не хватает.
            if new_balance is None:
                current_balance = await get_balance(
                    guild_id=self.guild_id,
                    user_id=self.player_id
                )

                await self.open_bet_selection(
                    interaction,
                    current_balance
                )

                return

            slots_view = SlotsView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet,
                balance_after_bet=new_balance
            )

            embed = casino_embed(
                title="🎡 Рулетка",
                description=(
                    "Колесо ждёт нового выбора.\n\n"
                    f"Ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    "Выбери сектор:"
                ),
            )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=roulette_view,
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

            current_balance = await get_balance(
                guild_id=self.guild_id,
                user_id=self.player_id
            )

            # В рулетке ставка ещё не списывается.
            # Сначала пользователь должен выбрать сектор.
            #
            # Но заранее проверяем,
            # способен ли он вообще повторить эту ставку.
            if current_balance < self.bet:
                await self.open_bet_selection(
                    interaction,
                    current_balance
                )

                return

            roulette_view = RouletteView(
                player_id=self.player_id,
                guild_id=self.guild_id,
                bet=self.bet
            )

            embed = casino_embed(
                title="🎡 Рулетка",
                description=(
                    "Колесо ждёт нового выбора.\n\n"
                    f"Ставка: "
                    f"**{self.bet} {CURRENCY_SYMBOL}**\n\n"
                    "Выбери сектор:"
                ),
            )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=roulette_view,
            )

            return

        raise ValueError(
            f"Неизвестная игра казино: {self.game}"
        )

    # =========================================================
    # ИЗМЕНИТЬ СТАВКУ
    # =========================================================

    @discord.ui.button(
        label="Изменить ставку",
        emoji="💰",
        style=discord.ButtonStyle.primary,
        custom_id="casino_change_bet"
    )
    async def change_bet(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not await self.begin_transition(
            interaction
        ):
            return

        current_balance = await get_balance(
            guild_id=self.guild_id,
            user_id=self.player_id
        )

        await self.open_bet_selection(
            interaction,
            current_balance
        )

    # =========================================================
    # В КАЗИНО
    # =========================================================

    @discord.ui.button(
        label="В казино",
        emoji="🎰",
        style=discord.ButtonStyle.secondary,
        custom_id="casino_back"
    )
    async def back_to_casino(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
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
                "Добро пожаловать за столы сада.\n\n"
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
        Через 180 секунд ResultView перестаёт быть активной.

        Кнопки визуально отключаются,
        чтобы пользователь не нажимал
        на уже мёртвую View.
        """

        # Если уже начался переход,
        # ничего дополнительно делать не нужно.
        if self.processing:
            return

        self.processing = True

        self.disable_all_buttons()

        # Если сообщение почему-то не было сохранено,
        # просто завершаем View.
        if self.message is None:
            self.stop()
            return

        try:
            await self.message.edit(
                view=self
            )

        except discord.NotFound:
            # Сообщение уже удалено.
            pass

        except discord.Forbidden as error:
            print(
                "[CASINO RESULT TIMEOUT FORBIDDEN]",
                repr(error)
            )

        except discord.HTTPException as error:
            print(
                "[CASINO RESULT TIMEOUT HTTP ERROR]",
                repr(error)
            )

        except Exception as error:
            print(
                "[CASINO RESULT TIMEOUT ERROR]",
                type(error).__name__,
                str(error)
            )

            traceback.print_exception(
                type(error),
                error,
                error.__traceback__
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
        item: discord.ui.Item
    ):
        """
        Ошибки callback больше не пропадают молча.
        """

        self.processing = False

        print(
            "[CASINO RESULT VIEW ERROR]",
            type(error).__name__,
            str(error)
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

        embed = error_embed(
            title="Ошибка казино",
            description=(
                "Во время перехода произошла ошибка.\n"
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
                repr(response_error)
            )