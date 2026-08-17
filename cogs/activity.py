import time

import discord
from discord.ext import commands

from database.member_stats import (
    add_voice_seconds,
    increment_messages,
)


class Activity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # (guild_id, user_id) -> время входа
        self.voice_sessions: dict[tuple[int, int], float] = {}


    # =========================
    # MESSAGES
    # =========================
    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ) -> None:
        if message.author.bot:
            return

        if message.guild is None:
            return

        await increment_messages(
            guild_id=message.guild.id,
            user_id=message.author.id
        )


    # =========================
    # VOICE
    # =========================
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        if member.bot:
            return

        # ВРЕМЕННАЯ ПРОВЕРКА
        print(
            f"{member.display_name}: "
            f"{before.channel} -> {after.channel}"
        )

        if before.channel == after.channel:
            return

        key = (
            member.guild.id,
            member.id
        )

        # Пользователь вошёл в голосовой канал
        if before.channel is None and after.channel is not None:
            self.voice_sessions[key] = time.monotonic()
            return

        # Пользователь вышел
        if before.channel is not None and after.channel is None:
            started_at = self.voice_sessions.pop(
                key,
                None
            )

            if started_at is None:
                return

            seconds = int(
                time.monotonic() - started_at
            )
            
            print(
                f"{member.display_name} провёл в voice: {seconds} сек."
            )

            await add_voice_seconds(
                guild_id=member.guild.id,
                user_id=member.id,
                seconds=seconds
            )

            return

        # Переход между голосовыми каналами
        if (
            before.channel is not None
            and after.channel is not None
        ):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Activity(bot))