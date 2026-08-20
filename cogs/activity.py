import time

import discord
from discord.ext import commands


from config.leveling import (
    MESSAGE_XP,
    MESSAGE_XP_COOLDOWN
)

from database.member_stats import (
    add_voice_seconds,
    record_message,
    ensure_members_exist,
)


class Activity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.voice_sessions: dict[
            tuple[int, int],
            float
        ] = {}

        self.last_message_xp: dict[
            tuple[int, int],
            float
        ] = {}


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

        key = (
            message.guild.id,
            message.author.id
        )

        now = time.monotonic()

        last_xp_time = self.last_message_xp.get(key)

        xp_gain = 0

        if (
            last_xp_time is None
            or now - last_xp_time >= MESSAGE_XP_COOLDOWN
        ):
            xp_gain = MESSAGE_XP
            self.last_message_xp[key] = now

        await record_message(
            guild_id=message.guild.id,
            user_id=message.author.id,
            xp_gain=xp_gain
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

        # Вход
        if (
            before.channel is None
            and after.channel is not None
        ):
            self.voice_sessions[key] = time.monotonic()
            return

        # Выход
        if (
            before.channel is not None
            and after.channel is None
        ):
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
                f"{member.display_name} "
                f"провёл в voice: {seconds} сек."
            )

            await add_voice_seconds(
                guild_id=member.guild.id,
                user_id=member.id,
                seconds=seconds
            )

            return

        # Переход между voice
        if (
            before.channel is not None
            and after.channel is not None
        ):
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Activity(bot))