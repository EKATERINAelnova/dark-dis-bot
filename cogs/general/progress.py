import discord

from discord import app_commands
from discord.ext import commands

from config.roles import LEVEL_ROLES
from services.member_progress import get_member_progress
from utils.embeds import eden_embed


def format_voice_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    if hours > 0:
        return f"{hours} ч {minutes} мин"

    return f"{minutes} мин"


def format_milestone(progress) -> str:
    if not LEVEL_ROLES:
        return "Список юбилейных ролей пока не настроен."

    lines = []

    if progress.current_milestone is None:
        lines.append("Текущая роль: **ещё не открыта**")
    else:
        level, role_name = progress.current_milestone
        lines.append(
            f"Текущая роль: **{role_name}** · уровень **{level}**"
        )

    if progress.next_milestone is None:
        lines.append("Следующая роль: **все milestone пройдены**")
    else:
        level, role_name = progress.next_milestone
        levels_left = max(0, level - progress.level)

        lines.append(
            f"Следующая роль: **{role_name}** · уровень **{level}**"
        )
        lines.append(
            f"До неё: **{levels_left} ур.**"
        )

    return "\n".join(lines)


class Progress(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="прогресс",
        description="Посмотреть общий прогресс участника сада",
    )
    @app_commands.guild_only()
    async def progress(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        if interaction.guild is None:
            return

        if user is None:
            user = interaction.user

        await interaction.response.defer()

        progress = await get_member_progress(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        stats = progress.stats
        activities = progress.activities

        embed = eden_embed(
            title="✦ ПУТЬ В САДУ",
            description=(
                f"Общий прогресс {user.mention} в LOST EDEN."
            ),
        )

        embed.add_field(
            name="ПРОГРЕСС",
            value=(
                f"Уровень: **{progress.level}**\n"
                f"XP: **{stats.xp}**\n"
                f"До следующего уровня: **{progress.xp_to_next_level} XP**\n"
                f"Место в рейтинге: **#{progress.rank}**\n"
                f"EDEN CASES: **{stats.eden_cases}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="АКТИВНОСТЬ",
            value=(
                f"Сообщений: **{stats.messages}**\n"
                f"В голосовых: **{format_voice_time(stats.voice_seconds)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="ЮБИЛЕЙНАЯ РОЛЬ",
            value=format_milestone(progress),
            inline=False,
        )

        embed.add_field(
            name="EVENTS",
            value=(
                f"Участий: **{activities.events.participations}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="DUELS",
            value=(
                f"Сыграно: **{activities.duels.participations}**\n"
                f"Побед: **{activities.duels.wins}**\n"
                f"Winrate: **{activities.duels.winrate}%**"
            ),
            inline=True,
        )

        embed.add_field(
            name="CLOSES",
            value=(
                f"Сыграно: **{activities.closes.participations}**\n"
                f"Побед: **{activities.closes.wins}**\n"
                f"Winrate: **{activities.closes.winrate}%**"
            ),
            inline=True,
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.set_footer(
            text=(
                "DUEL и CLOSE учитываются только после подтверждения результата"
            )
        )

        await interaction.followup.send(
            embed=embed
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Progress(bot)
    )
