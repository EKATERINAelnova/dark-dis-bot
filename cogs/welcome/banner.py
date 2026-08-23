import asyncio
import logging

import discord

from discord.ext import (
    commands,
    tasks,
)

from utils.server_banner import (
    create_server_banner,
)


logger = logging.getLogger(
    "lost_eden.banner"
)


# =========================================================
# SETTINGS
# =========================================================

BANNER_UPDATE_INTERVAL = 60


class Banner(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

        # Последние успешно установленные
        # значения счётчиков для каждого сервера.
        self.last_counts: dict[
            int,
            tuple[int, int],
        ] = {}

    # =========================================================
    # COG LIFECYCLE
    # =========================================================

    async def cog_load(
        self,
    ) -> None:
        self.update_banner.start()

    async def cog_unload(
        self,
    ) -> None:
        self.update_banner.cancel()

    # =========================================================
    # UPDATE LOOP
    # =========================================================

    @tasks.loop(
        seconds=BANNER_UPDATE_INTERVAL
    )
    async def update_banner(
        self,
    ) -> None:
        """
        Проверяет состояние серверов.

        Сам баннер изменяется только тогда,
        когда количество участников
        или online-пользователей поменялось.
        """

        for guild in self.bot.guilds:
            try:
                await self.update_guild_banner(
                    guild
                )

            except Exception:
                logger.exception(
                    (
                        "Неожиданная ошибка "
                        "обновления баннера | "
                        "guild=%s (%s)"
                    ),
                    guild.name,
                    guild.id,
                )

    # =========================================================
    # GUILD BANNER
    # =========================================================

    async def update_guild_banner(
        self,
        guild: discord.Guild,
    ) -> None:

        # =====================================================
        # FEATURE CHECK
        # =====================================================

        if (
            "BANNER"
            not in guild.features
        ):
            return

        # =====================================================
        # PERMISSION CHECK
        # =====================================================

        bot_member = guild.me

        if bot_member is None:
            return

        if (
            not bot_member.guild_permissions.manage_guild
        ):
            logger.warning(
                (
                    "Нет права Manage Server "
                    "для обновления баннера | "
                    "guild=%s (%s)"
                ),
                guild.name,
                guild.id,
            )

            return

        # =====================================================
        # COUNTERS
        # =====================================================

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

        counts = (
            online_count,
            member_count,
        )

        # Ничего не изменилось.
        # Discord API вообще не вызываем.
        if (
            self.last_counts.get(
                guild.id
            )
            == counts
        ):
            return

        # =====================================================
        # RENDER
        # =====================================================

        # Pillow работает синхронно.
        #
        # Выносим генерацию баннера
        # из event loop, чтобы она
        # не тормозила slash-команды
        # и остальные события Discord.
        banner = await asyncio.to_thread(
            create_server_banner,
            online_count=online_count,
            member_count=member_count,
        )

        # =====================================================
        # DISCORD UPDATE
        # =====================================================

        try:
            await guild.edit(
                banner=banner,
                reason=(
                    "Обновление счётчика LOST EDEN"
                ),
            )

        except discord.Forbidden:
            logger.warning(
                (
                    "Discord запретил "
                    "изменение баннера | "
                    "guild=%s (%s)"
                ),
                guild.name,
                guild.id,
            )

            return

        except discord.HTTPException as error:
            logger.warning(
                (
                    "Ошибка Discord API "
                    "при обновлении баннера | "
                    "guild=%s (%s) | "
                    "status=%s | error=%s"
                ),
                guild.name,
                guild.id,
                error.status,
                error,
            )

            return

        # Запоминаем counts только
        # после успешного guild.edit().
        self.last_counts[
            guild.id
        ] = counts

        logger.info(
            (
                "Баннер обновлён | "
                "guild=%s | "
                "online=%s | members=%s"
            ),
            guild.name,
            online_count,
            member_count,
        )

    # =========================================================
    # BEFORE LOOP
    # =========================================================

    @update_banner.before_loop
    async def before_update_banner(
        self,
    ) -> None:
        await self.bot.wait_until_ready()


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Banner(bot)
    )