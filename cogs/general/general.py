import discord

from discord import app_commands
from discord.ext import commands

from config.theme import EDEN_GOLD

from database.member_stats import (
    get_member_stats,
    get_member_rank,
)

from utils.profile_card import (
    ProfileStats,
    create_profile_card,
)

from utils.server_banner import (
    create_server_banner,
)

from utils.leveling import (
    level_from_xp,
    xp_to_next_level,
)

from utils.embeds import (
    eden_embed,
    error_embed,
)

from views.info_view import ServerInfoView
from views.leaderboard_view import LeaderboardView


class General(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    # =========================================================
    # TEST BANNER
    # =========================================================

    @app_commands.command(
        name="testbanner",
        description="Тест обновления баннера",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def testbanner(
        self,
        interaction: discord.Interaction,
    ):
        """
        Ручное тестовое обновление баннера.

        Доступно только администраторам.
        """

        guild = interaction.guild

        if guild is None:
            return

        # Сразу подтверждаем interaction,
        # потому что генерация изображения
        # и guild.edit могут занять время.
        await interaction.response.defer(
            ephemeral=True
        )

        online_count = sum(
            1
            for member in guild.members
            if (
                not member.bot
                and member.status
                != discord.Status.offline
            )
        )

        member_count = sum(
            1
            for member in guild.members
            if not member.bot
        )

        banner = create_server_banner(
            online_count,
            member_count,
        )

        await guild.edit(
            banner=banner,
            reason=(
                "Тест динамического баннера"
            ),
        )

        embed = eden_embed(
            title="🌿 Баннер обновлён",
            description=(
                f"В саду: "
                f"**{online_count}**\n"
                f"Всего душ: "
                f"**{member_count}**"
            ),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )

    # =========================================================
    # PING
    # =========================================================

    @app_commands.command(
        name="ping",
        description="Проверить работу бота",
    )
    async def ping(
        self,
        interaction: discord.Interaction,
    ):
        embed = eden_embed(
            title="🌿 Связь с садом",
            description=(
                "Сад отвечает.\n"
                f"Задержка: "
                f"`{round(self.bot.latency * 1000)} ms`"
            ),
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =========================================================
    # PROFILE
    # =========================================================

    @app_commands.command(
        name="profile",
        description=(
            "Открыть профиль участника сада"
        ),
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        if interaction.guild is None:
            embed = error_embed(
                title="Профиль недоступен",
                description=(
                    "Профиль можно открыть "
                    "только внутри сервера."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        if user is None:
            user = interaction.user

        await interaction.response.defer()

        db_stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        level = level_from_xp(
            db_stats.xp
        )

        rank = await get_member_rank(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        xp_left = xp_to_next_level(
            db_stats.xp
        )

        profile_stats = ProfileStats(
            level=level,
            rank=rank,
            total_xp=db_stats.xp,
            xp_to_next_level=xp_left,
            currency=db_stats.currency,
            messages=db_stats.messages,
            voice_seconds=db_stats.voice_seconds,
        )

        card = await create_profile_card(
            user,
            profile_stats,
        )

        file = discord.File(
            card,
            filename="profile.png",
        )

        await interaction.followup.send(
            file=file
        )

    # =========================================================
    # USER INFO
    # =========================================================

    @app_commands.command(
        name="userinfo",
        description=(
            "Информация об участнике сада"
        ),
    )
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        if user.joined_at is None:
            joined_text = "Неизвестно"
        else:
            joined_text = (
                user.joined_at.strftime(
                    "%d.%m.%Y"
                )
            )

        created_text = (
            user.created_at.strftime(
                "%d.%m.%Y"
            )
        )

        roles_text = ", ".join(
            role.mention
            for role in user.roles
            if role.name != "@everyone"
        )

        if not roles_text:
            roles_text = (
                "Пока без выбранных ролей"
            )

        embed = discord.Embed(
            title="🌿 Путник сада",
            description=(
                f"{user.mention}\n"
                "*Каждый приходит сюда "
                "со своей дорогой за спиной.*"
            ),
            colour=EDEN_GOLD,
        )

        embed.add_field(
            name="Имя",
            value=user.display_name,
            inline=True,
        )

        embed.add_field(
            name="В саду с",
            value=joined_text,
            inline=True,
        )

        embed.add_field(
            name="Путь начался",
            value=created_text,
            inline=True,
        )

        embed.add_field(
            name="Корни и состояния",
            value=roles_text,
            inline=False,
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.set_footer(
            text=(
                f"LOST EDEN · RIMAY  •  "
                f"ID {user.id}"
            )
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =========================================================
    # SERVER INFO
    # =========================================================

    @app_commands.command(
        name="serverinfo",
        description="Открыть карту LOST EDEN",
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction,
    ):
        guild = interaction.guild

        if guild is None:
            embed = error_embed(
                title="Карта недоступна",
                description=(
                    "Карта сада доступна "
                    "только внутри сервера."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        view = ServerInfoView(
            guild=guild,
            user_id=interaction.user.id,
        )

        await interaction.response.send_message(
            embed=view.main_embed(),
            view=view,
        )

        view.message = (
            await interaction.original_response()
        )


    # =========================================================
    # EDEN CASES
    # =========================================================

    @app_commands.command(
        name="cases",
        description="Открыть хранилище EDEN CASES",
    )
    @app_commands.guild_only()
    async def cases(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return

        stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
        )

        level = level_from_xp(
            stats.xp
        )

        xp_left = xp_to_next_level(
            stats.xp
        )

        cases_count = stats.eden_cases

        if cases_count == 0:
            cases_text = (
                "В хранилище пока тихо.\n"
                "Следующий EDEN CASE появится, "
                "когда ты достигнешь нового уровня."
            )
        elif cases_count == 1:
            cases_text = (
                "В хранилище ждёт "
                "**1 EDEN CASE**."
            )
        else:
            cases_text = (
                f"В хранилище ждут "
                f"**{cases_count} EDEN CASES**."
            )

        embed = eden_embed(
            title="✦ EDEN CASES",
            description=(
                f"{cases_text}\n\n"
                "*То, что сад сохраняет для тех, "
                "кто продолжает свой путь.*"
            ),
        )

        embed.add_field(
            name="Хранилище",
            value=f"`{cases_count}`",
            inline=True,
        )

        embed.add_field(
            name="Уровень",
            value=f"`{level}`",
            inline=True,
        )

        embed.add_field(
            name="До следующего кейса",
            value=f"`{xp_left} XP`",
            inline=True,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
    
    # =========================================================
    # LEADERBOARD
    # =========================================================

    @app_commands.command(
        name="leaderboard",
        description=(
            "Посмотреть рейтинг участников сада"
        ),
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            embed = error_embed(
                title="Рейтинг недоступен",
                description=(
                    "Рейтинг можно открыть "
                    "только внутри сервера."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        await interaction.response.defer()

        view = LeaderboardView(
            guild=interaction.guild,
            player_id=interaction.user.id,
        )

        embed = await view.build_embed()

        # ВАЖНО:
        # сохраняем отправленное сообщение,
        # чтобы LeaderboardView.on_timeout()
        # смог отключить кнопки.
        message = await interaction.followup.send(
            embed=embed,
            view=view,
            wait=True,
        )

        view.bind_message(
            message
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        General(bot)
    )