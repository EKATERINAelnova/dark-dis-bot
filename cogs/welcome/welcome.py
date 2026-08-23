import logging
import os

import discord

from discord.ext import commands

from config.theme import EDEN_GOLD
from database.member_stats import ensure_members_exist


logger = logging.getLogger(
    "lost_eden.welcome"
)


class Welcome(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

        raw_channel_id = os.getenv(
            "WELCOME_CHANNEL_ID"
        )

        if (
            raw_channel_id
            and raw_channel_id.strip().isdigit()
        ):
            self.welcome_channel_id = int(
                raw_channel_id.strip()
            )

        else:
            self.welcome_channel_id = None

            logger.warning(
                "WELCOME_CHANNEL_ID "
                "не задан или имеет "
                "неверный формат"
            )

    # =========================================================
    # EMBED
    # =========================================================

    def create_welcome_embed(
        self,
        member: discord.Member,
        guild: discord.Guild,
    ) -> discord.Embed:
        member_count = sum(
            1
            for guild_member in guild.members
            if not guild_member.bot
        )

        embed = discord.Embed(
            title=(
                "🌘 LOST EDEN · "
                "НОВАЯ ДУША В САДУ"
            ),
            description=(
                f"Приветствуем в Саду, "
                f"{member.mention}!\n\n"

                f"Ты стал(а) "
                f"**{member_count}-й** душой, "
                f"нашедшей пристанище "
                f"в **LOST EDEN**.\n\n"

                f"📜 **Первые шаги:**\n"
                f"• Ознакомься с правилами "
                f"и структурой сервера\n"
                f"• Проверь свой статус "
                f"и карточку через `/profile`\n"
                f"• Присоединяйся к общению "
                f"в текстовых и голосовых "
                f"каналах\n\n"

                f"> *«We don't return. "
                f"We rebuild.»*"
            ),
            color=EDEN_GOLD,
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        footer_icon = (
            guild.icon.url
            if guild.icon
            else None
        )

        embed.set_footer(
            text="LOST EDEN · RIMAY",
            icon_url=footer_icon,
        )

        return embed

    # =========================================================
    # MEMBER JOIN
    # =========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member,
    ) -> None:
        if member.bot:
            return

        guild = member.guild

        # =====================================================
        # DATABASE
        # =====================================================

        try:
            await ensure_members_exist(
                guild_id=guild.id,
                user_ids=[
                    member.id
                ],
            )

            logger.info(
                (
                    "Добавлен новый участник "
                    "в базу | guild=%s | "
                    "user=%s (%s)"
                ),
                guild.name,
                member,
                member.id,
            )

        except Exception:
            # Ошибка БД не должна уничтожить
            # само welcome-сообщение.
            #
            # Activity позже сможет создать
            # запись участника повторно.
            logger.exception(
                (
                    "Не удалось зарегистрировать "
                    "участника в базе | "
                    "guild=%s | user=%s"
                ),
                guild.id,
                member.id,
            )

        # =====================================================
        # CONFIG
        # =====================================================

        if self.welcome_channel_id is None:
            return

        # =====================================================
        # CHANNEL
        # =====================================================

        channel = guild.get_channel(
            self.welcome_channel_id
        )

        if channel is None:
            logger.warning(
                (
                    "Welcome-канал не найден | "
                    "guild=%s (%s) | "
                    "channel_id=%s"
                ),
                guild.name,
                guild.id,
                self.welcome_channel_id,
            )

            return

        # В .env можно случайно вставить
        # ID голосового канала или категории.
        if not isinstance(
            channel,
            discord.TextChannel,
        ):
            logger.warning(
                (
                    "WELCOME_CHANNEL_ID "
                    "указывает не на "
                    "текстовый канал | "
                    "guild=%s | "
                    "channel_id=%s | "
                    "type=%s"
                ),
                guild.id,
                channel.id,
                type(channel).__name__,
            )

            return

        # =====================================================
        # EMBED
        # =====================================================

        embed = self.create_welcome_embed(
            member=member,
            guild=guild,
        )

        # =====================================================
        # SEND
        # =====================================================

        try:
            await channel.send(
                content=(
                    f"Добро пожаловать, "
                    f"{member.mention}!"
                ),
                embed=embed,
            )

        except discord.Forbidden:
            logger.warning(
                (
                    "Нет прав на отправку "
                    "welcome-сообщения | "
                    "guild=%s | "
                    "channel=%s (%s)"
                ),
                guild.name,
                channel.name,
                channel.id,
            )

            return

        except discord.HTTPException as error:
            logger.warning(
                (
                    "Ошибка Discord API "
                    "при отправке welcome | "
                    "guild=%s | "
                    "channel=%s | "
                    "status=%s | "
                    "error=%s"
                ),
                guild.id,
                channel.id,
                error.status,
                error,
            )

            return

        except Exception:
            logger.exception(
                (
                    "Неожиданная ошибка "
                    "welcome-системы | "
                    "guild=%s | user=%s"
                ),
                guild.id,
                member.id,
            )

            return

        logger.info(
            (
                "Welcome отправлен | "
                "guild=%s | "
                "user=%s (%s) | "
                "channel=%s"
            ),
            guild.name,
            member,
            member.id,
            channel.id,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Welcome(bot)
    )