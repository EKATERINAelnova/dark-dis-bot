import os
import discord
from discord import app_commands
from discord.ext import commands

from config.theme import EDEN_GOLD, EDEN_ASH
from database.member_stats import ensure_members_exist

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        raw_channel_id = os.getenv("WELCOME_CHANNEL_ID")
        self.welcome_channel_id = (
            int(raw_channel_id)
            if raw_channel_id and raw_channel_id.isdigit()
            else None
        )

    def create_welcome_embed(
        self,
        member: discord.Member,
        guild: discord.Guild
    ) -> discord.Embed:
        member_count = sum(1 for m in guild.members if not m.bot)

        embed = discord.Embed(
            title="🌘 LOST EDEN · НОВАЯ ДУША В САДУ",
            description=(
                f"Приветствуем в Саду, {member.mention}!\n\n"
                f"Ты стал(а) **{member_count}-й** душой, "
                f"нашедшей пристанище в **LOST EDEN**.\n\n"
                f"📜 **Первые шаги:**\n"
                f"• Ознакомься с правилами и структурой сервера\n"
                f"• Проверь свой статус и карточку через `/profile`\n"
                f"• Присоединяйся к общению в текстовых и голосовых каналах\n\n"
                f"> *«We don't return. We rebuild.»*"
            ),
            color=EDEN_GOLD
        )

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        footer_icon = guild.icon.url if guild.icon else None
        embed.set_footer(
            text="LOST EDEN · RIMAY",
            icon_url=footer_icon
        )

        return embed

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ) -> None:
        if member.bot:
            return

        guild = member.guild

        # Сначала регистрируем участника в системе
        await ensure_members_exist(
            guild_id=guild.id,
            user_ids=[member.id],
        )

        print(
            f"[DB] Добавлен новый участник: "
            f"{member.display_name}"
        )

        # Welcome может быть не настроен,
        # но участник уже останется в БД.
        if not self.welcome_channel_id:
            print(
                "[WELCOME] "
                "WELCOME_CHANNEL_ID не задан в .env"
            )
            return

        channel = guild.get_channel(
            self.welcome_channel_id
        )

        if channel is None:
            print(
                f"[WELCOME] Канал с ID "
                f"{self.welcome_channel_id} "
                f"не найден на сервере {guild.name}"
            )
            return

        embed = self.create_welcome_embed(
            member,
            guild
        )

        try:
            await channel.send(
                content=(
                    f"Добро пожаловать, "
                    f"{member.mention}!"
                ),
                embed=embed
            )

            print(
                f"[WELCOME] Отправлено приветствие "
                f"для {member} "
                f"на сервере {guild.name}"
            )

        except discord.Forbidden:
            print(
                f"[WELCOME] Нет прав "
                f"на отправку сообщений "
                f"в канал {channel.name} "
                f"({channel.id})"
            )

        except discord.HTTPException as error:
            print(
                f"[WELCOME] Ошибка при отправке "
                f"приветствия: {error}"
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))