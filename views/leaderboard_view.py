import traceback

import discord

from config.economy import CURRENCY_SYMBOL
from database.leaderboard import (
    LeaderboardCategory,
    get_leaderboard,
    get_leaderboard_rank,
)
from database.member_stats import get_member_stats
from utils.leveling import level_from_xp
from utils.embeds import (
    eden_embed,
    error_embed,
)


# =========================================================
# CATEGORY
# =========================================================

CATEGORY_TITLES = {
    "xp": "🌿 УРОВЕНЬ",
    "messages": "💬 СООБЩЕНИЯ",
    "voice": "🎙️ ГОЛОС",
    "currency": f"{CURRENCY_SYMBOL} БАЛАНС",
}


CATEGORY_DESCRIPTIONS = {
    "xp": (
        "Самые укоренившиеся души сада"
    ),
    "messages": (
        "Те, чьи голоса чаще всего "
        "слышны в саду"
    ),
    "voice": (
        "Те, кто дольше всего "
        "остаётся у костра"
    ),
    "currency": (
        "Самые состоятельные жители сада"
    ),
}


MEDALS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


# =========================================================
# FORMATTERS
# =========================================================

def format_voice_time(
    seconds: int,
) -> str:
    hours = (
        seconds // 3600
    )

    minutes = (
        seconds % 3600
    ) // 60

    if hours > 0:
        return (
            f"{hours}ч {minutes}м"
        )

    return f"{minutes}м"


def format_value(
    category: LeaderboardCategory,
    stats,
) -> str:
    if category == "xp":
        level = level_from_xp(
            stats.xp
        )

        return (
            f"Lv. {level} · "
            f"{stats.xp:,} XP"
        ).replace(
            ",",
            " ",
        )

    if category == "messages":
        return (
            f"{stats.messages:,} "
            "сообщений"
        ).replace(
            ",",
            " ",
        )

    if category == "voice":
        return format_voice_time(
            stats.voice_seconds
        )

    if category == "currency":
        return (
            f"{stats.currency:,} "
            f"{CURRENCY_SYMBOL}"
        ).replace(
            ",",
            " ",
        )

    return "—"


# =========================================================
# VIEW
# =========================================================

class LeaderboardView(
    discord.ui.View
):
    def __init__(
        self,
        guild: discord.Guild,
        player_id: int,
        category: LeaderboardCategory = "xp",
    ):
        super().__init__(
            timeout=60
        )

        self.guild = guild
        self.player_id = player_id
        self.category = category

        self.processing = False

        self.message: (
            discord.Message
            | discord.InteractionMessage
            | None
        ) = None

        self.update_button_styles()

    # =====================================================
    # MESSAGE
    # =====================================================

    def bind_message(
        self,
        message: (
            discord.Message
            | discord.InteractionMessage
        ),
    ) -> None:
        """
        Сохраняет сообщение,
        к которому привязана View.

        Нужно для корректного timeout.
        """

        self.message = message

    # =====================================================
    # INTERACTION CHECK
    # =====================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if (
            interaction.user.id
            == self.player_id
        ):
            return True

        embed = error_embed(
            title="Чужой рейтинг",
            description=(
                "Этот рейтинг открыт "
                "другим участником сада.\n\n"
                "Открой свой через "
                "`/leaderboard`."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

        return False

    # =====================================================
    # BUTTONS
    # =====================================================

    def disable_all_buttons(
        self,
    ) -> None:
        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

    def update_button_styles(
        self,
    ) -> None:
        buttons = {
            "xp": self.level_button,
            "messages": self.messages_button,
            "voice": self.voice_button,
            "currency": self.currency_button,
        }

        for (
            category,
            button,
        ) in buttons.items():

            if (
                category
                == self.category
            ):
                button.style = (
                    discord.ButtonStyle.primary
                )

            else:
                button.style = (
                    discord.ButtonStyle.secondary
                )

    # =====================================================
    # EMBED
    # =====================================================

    async def build_embed(
        self,
    ) -> discord.Embed:
        leaderboard = await get_leaderboard(
            guild_id=self.guild.id,
            category=self.category,
            limit=50,
        )

        player_stats = (
            await get_member_stats(
                guild_id=self.guild.id,
                user_id=self.player_id,
            )
        )

        player_rank = (
            await get_leaderboard_rank(
                guild_id=self.guild.id,
                user_id=self.player_id,
                category=self.category,
            )
        )

        title = CATEGORY_TITLES[
            self.category
        ]

        description = (
            CATEGORY_DESCRIPTIONS[
                self.category
            ]
        )

        embed = eden_embed(
            title=(
                f"LOST EDEN · {title}"
            ),
            description=(
                f"*{description}*\n\n"
            ),
        )

        lines: list[str] = []

        shown = 0

        # =================================================
        # TOP
        # =================================================

        for stats in leaderboard:
            member = (
                self.guild.get_member(
                    stats.user_id
                )
            )

            # Пользователь уже
            # покинул сервер.
            if member is None:
                continue

            # Ботов не показываем.
            if member.bot:
                continue

            shown += 1

            if shown > 10:
                break

            medal = MEDALS.get(
                shown,
                f"`{shown}.`",
            )

            name = (
                discord.utils.escape_markdown(
                    member.display_name
                )
            )

            value = format_value(
                self.category,
                stats,
            )

            lines.append(
                f"{medal} **{name}**\n"
                f"　└ {value}"
            )

        if lines:
            embed.description += (
                "\n\n".join(
                    lines
                )
            )

        else:
            embed.description += (
                "В саду пока "
                "слишком тихо..."
            )

        # =================================================
        # PLAYER
        # =================================================

        player_value = format_value(
            self.category,
            player_stats,
        )

        if player_rank > 0:
            rank_text = (
                f"**#{player_rank}**"
            )

        else:
            rank_text = (
                "**Вне рейтинга**"
            )

        embed.add_field(
            name="🌱 Твоё место",
            value=(
                f"{rank_text}\n"
                f"{player_value}"
            ),
            inline=False,
        )

        embed.set_footer(
            text=(
                "Рейтинг обновляется "
                "вместе с активностью сада"
            )
        )

        return embed

    # =====================================================
    # CHANGE CATEGORY
    # =====================================================

    async def change_category(
        self,
        interaction: discord.Interaction,
        category: LeaderboardCategory,
    ) -> None:
        if self.processing:
            return

        self.processing = True

        try:
            await interaction.response.defer()

            self.category = category

            self.update_button_styles()

            embed = await self.build_embed()

            self.message = (
                await interaction.edit_original_response(
                    embed=embed,
                    view=self,
                )
            )

        finally:
            self.processing = False

    # =====================================================
    # LEVEL
    # =====================================================

    @discord.ui.button(
        label="Уровень",
        emoji="🌿",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def level_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_category(
            interaction,
            "xp",
        )

    # =====================================================
    # MESSAGES
    # =====================================================

    @discord.ui.button(
        label="Сообщения",
        emoji="💬",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def messages_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_category(
            interaction,
            "messages",
        )

    # =====================================================
    # VOICE
    # =====================================================

    @discord.ui.button(
        label="Голос",
        emoji="🎙️",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def voice_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_category(
            interaction,
            "voice",
        )

    # =====================================================
    # BALANCE
    # =====================================================

    @discord.ui.button(
        label="Баланс",
        emoji="💰",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def currency_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.change_category(
            interaction,
            "currency",
        )

    # =====================================================
    # TIMEOUT
    # =====================================================

    async def on_timeout(
        self,
    ) -> None:
        self.disable_all_buttons()

        if self.message is None:
            self.stop()
            return

        try:
            # Берём embed из текущего сообщения.
            if self.message.embeds:
                embed = (
                    self.message.embeds[0]
                )

                embed.set_footer(
                    text=(
                        "🌿 Рейтинг устарел · "
                        "открой /leaderboard снова"
                    )
                )

                await self.message.edit(
                    embed=embed,
                    view=self,
                )

            else:
                await self.message.edit(
                    view=self,
                )

        except discord.NotFound:
            # Сообщение уже удалено.
            pass

        except discord.Forbidden as error:
            print(
                "[LEADERBOARD TIMEOUT FORBIDDEN]",
                repr(error),
            )

        except discord.HTTPException as error:
            print(
                "[LEADERBOARD TIMEOUT HTTP ERROR]",
                repr(error),
            )

        except Exception as error:
            print(
                "[LEADERBOARD TIMEOUT ERROR]",
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

    # =====================================================
    # ERROR
    # =====================================================

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ) -> None:
        self.processing = False

        print(
            "[LEADERBOARD VIEW ERROR]",
            type(error).__name__,
            str(error),
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
        )

        embed = error_embed(
            title="Ошибка рейтинга",
            description=(
                "Не удалось обновить рейтинг.\n"
                "Попробуй открыть "
                "`/leaderboard` заново."
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
                "[LEADERBOARD RESPONSE ERROR]",
                repr(response_error),
            )