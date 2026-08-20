import discord

from config.economy import CURRENCY_SYMBOL
from database.leaderboard import (
    LeaderboardCategory,
    get_leaderboard,
    get_leaderboard_rank,
)
from database.member_stats import get_member_stats
from utils.leveling import level_from_xp


CATEGORY_TITLES = {
    "xp": "🌿 УРОВЕНЬ",
    "messages": "💬 СООБЩЕНИЯ",
    "voice": "🎙️ ГОЛОС",
    "currency": f"{CURRENCY_SYMBOL} БАЛАНС",
}


CATEGORY_DESCRIPTIONS = {
    "xp": "Самые укоренившиеся души сада",
    "messages": "Те, чьи голоса чаще всего слышны в саду",
    "voice": "Те, кто дольше всего остаётся у костра",
    "currency": "Самые состоятельные жители сада",
}


MEDALS = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
}


def format_voice_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}ч {minutes}м"

    return f"{minutes}м"


def format_value(
    category: LeaderboardCategory,
    stats,
) -> str:
    if category == "xp":
        level = level_from_xp(stats.xp)

        return (
            f"Lv. {level} · "
            f"{stats.xp:,} XP"
        ).replace(",", " ")

    if category == "messages":
        return (
            f"{stats.messages:,} сообщений"
        ).replace(",", " ")

    if category == "voice":
        return format_voice_time(
            stats.voice_seconds
        )

    if category == "currency":
        return (
            f"{stats.currency:,} "
            f"{CURRENCY_SYMBOL}"
        ).replace(",", " ")

    return "—"


class LeaderboardView(discord.ui.View):
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

        self.message: discord.Message | None = None

        self.update_button_styles()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "Этот рейтинг открыт другой душой сада.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self):
        #
        # После окончания времени отключаем кнопки,
        # чтобы Discord не показывал
        # "Приложение не ответило вовремя".
        #
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is None:
            return

        if not self.message.embeds:
            return

        embed = self.message.embeds[0]

        embed.set_footer(
            text=(
                "🌿 Рейтинг устарел · "
                "открой /leaderboard снова"
            )
        )

        try:
            await self.message.edit(
                embed=embed,
                view=self,
            )
        except discord.HTTPException:
            pass

    def update_button_styles(self):
        buttons = {
            "xp": self.level_button,
            "messages": self.messages_button,
            "voice": self.voice_button,
            "currency": self.currency_button,
        }

        for category, button in buttons.items():
            if category == self.category:
                button.style = (
                    discord.ButtonStyle.primary
                )
            else:
                button.style = (
                    discord.ButtonStyle.secondary
                )

    async def build_embed(
        self,
    ) -> discord.Embed:
        leaderboard = await get_leaderboard(
            guild_id=self.guild.id,
            category=self.category,
            limit=50,
        )

        player_stats = await get_member_stats(
            guild_id=self.guild.id,
            user_id=self.player_id,
        )

        player_rank = await get_leaderboard_rank(
            guild_id=self.guild.id,
            user_id=self.player_id,
            category=self.category,
        )

        title = CATEGORY_TITLES[
            self.category
        ]

        description = CATEGORY_DESCRIPTIONS[
            self.category
        ]

        embed = discord.Embed(
            title=f"LOST EDEN · {title}",
            description=(
                f"*{description}*\n\n"
            ),
        )

        lines = []
        shown = 0

        for stats in leaderboard:
            member = self.guild.get_member(
                stats.user_id
            )

            #
            # Пользователь покинул сервер.
            #
            if member is None:
                continue

            #
            # Ботов не показываем.
            #
            if member.bot:
                continue

            shown += 1

            if shown > 10:
                break

            medal = MEDALS.get(
                shown,
                f"`{shown}.`",
            )

            name = discord.utils.escape_markdown(
                member.display_name
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
                "\n\n".join(lines)
            )
        else:
            embed.description += (
                "В саду пока слишком тихо..."
            )

        player_value = format_value(
            self.category,
            player_stats,
        )

        embed.add_field(
            name="🌱 Твоё место",
            value=(
                f"**#{player_rank}**\n"
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

    async def change_category(
        self,
        interaction: discord.Interaction,
        category: LeaderboardCategory,
    ):
        self.category = category

        self.update_button_styles()

        embed = await self.build_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

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