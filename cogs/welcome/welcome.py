import os
import discord
from discord import app_commands
from discord.ext import commands

from config.theme import EDEN_GOLD, EDEN_ASH

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
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        if not self.welcome_channel_id:
            print("[WELCOME] WELCOME_CHANNEL_ID не задан в .env")
            return

        guild = member.guild
        channel = guild.get_channel(self.welcome_channel_id)

        if channel is None:
            print(
                f"[WELCOME] Канал с ID {self.welcome_channel_id} "
                f"не найден на сервере {guild.name}"
            )
            return

        embed = self.create_welcome_embed(member, guild)

        try:
            await channel.send(
                content=f"Добро пожаловать, {member.mention}!",
                embed=embed
            )
            print(
                f"[WELCOME] Отправлено приветствие для {member} "
                f"на сервере {guild.name}"
            )
        except discord.Forbidden:
            print(
                f"[WELCOME] Нет прав на отправку сообщений "
                f"в канал {channel.name} ({channel.id})"
            )
        except discord.HTTPException as error:
            print(
                f"[WELCOME] Ошибка при отправке приветствия: {error}"
            )

    @app_commands.command(
        name="testwelcome",
        description="Проверить отображение приветствия нового участника"
    )
    async def testwelcome(
        self,
        interaction: discord.Interaction,
        target_user: discord.Member | None = None
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        member = target_user or interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(member.id) or interaction.user

        embed = self.create_welcome_embed(member, interaction.guild)

        await interaction.response.send_message(
            content=f"*(Тестовое приветствие)*\nДобро пожаловать, {member.mention}!",
            embed=embed,
            ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
