import time
from services.achievements import check_achievements
import discord

from discord.ext import (
    commands,
    tasks,
)

from config.leveling import (
    MESSAGE_XP,
    MESSAGE_XP_COOLDOWN,
)

from database.member_stats import (
    add_voice_seconds,
    record_message,
    ensure_members_exist,
)
from services.level_roles import sync_level_role

# =========================================================
# SETTINGS
# =========================================================

VOICE_SAVE_INTERVAL = 60


class Activity(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

        # key:
        # (guild_id, user_id)
        #
        # value:
        # момент, с которого ещё не сохранено
        # voice-время пользователя.
        self.voice_sessions: dict[
            tuple[int, int],
            float,
        ] = {}

        # Последний момент начисления
        # message XP.
        self.last_message_xp: dict[
            tuple[int, int],
            float,
        ] = {}

    # =========================================================
    # COG LIFECYCLE
    # =========================================================

    async def cog_load(
        self,
    ) -> None:
        """
        Запускает периодическое сохранение
        voice-времени.
        """

        self.voice_save_loop.start()

    async def cog_unload(
        self,
    ) -> None:
        """
        Останавливает фоновую задачу
        при выгрузке Cog.
        """

        self.voice_save_loop.cancel()

    # =========================================================
    # INITIAL STATE
    # =========================================================

    async def initialize_current_state(
        self,
    ) -> None:
        """
        Синхронизирует Activity
        с текущим состоянием Discord.

        В частности, начинает считать время
        пользователей, которые уже находились
        в voice на момент запуска бота.
        """

        now = time.monotonic()

        for guild in self.bot.guilds:
            # =============================================
            # DATABASE MEMBERS
            # =============================================

            user_ids = [
                member.id
                for member in guild.members
                if not member.bot
            ]

            await ensure_members_exist(
                guild_id=guild.id,
                user_ids=user_ids,
            )

            # =============================================
            # ACTIVE VOICE MEMBERS
            # =============================================

            for voice_channel in (
                guild.voice_channels
            ):
                for member in (
                    voice_channel.members
                ):
                    if member.bot:
                        continue

                    key = (
                        guild.id,
                        member.id,
                    )

                    # setdefault важен.
                    #
                    # on_ready может сработать повторно
                    # после reconnect.
                    #
                    # Уже активную сессию нельзя
                    # начинать заново.
                    self.voice_sessions.setdefault(
                        key,
                        now,
                    )

    # =========================================================
    # READY
    # =========================================================

    @commands.Cog.listener()
    async def on_ready(
        self,
    ) -> None:
        """
        Discord может вызвать on_ready
        несколько раз после reconnect.

        initialize_current_state()
        безопасен для повторного вызова.
        """

        await self.initialize_current_state()

    # =========================================================
    # MESSAGES
    # =========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message,
    ) -> None:
        if message.author.bot:
            return

        if message.guild is None:
            return

        key = (
            message.guild.id,
            message.author.id,
        )

        now = time.monotonic()

        last_xp_time = (
            self.last_message_xp.get(
                key
            )
        )

        xp_gain = 0

        if (
            last_xp_time is None
            or (
                now - last_xp_time
                >= MESSAGE_XP_COOLDOWN
            )
        ):
            xp_gain = MESSAGE_XP

            self.last_message_xp[
                key
            ] = now

        # Сообщение учитывается всегда.
        #
        # XP начисляется только тогда,
        # когда прошёл cooldown.
        cases_gained, new_level = await record_message(
            guild_id=message.guild.id,
            user_id=message.author.id,
            xp_gain=xp_gain,
        )

        if cases_gained > 0:
            member = message.guild.get_member(
                message.author.id
            )

            if member is not None:
                try:
                    await sync_level_role(
                        member=member,
                        level=new_level,
                    )
                except (
                    discord.HTTPException,
                    RuntimeError,
                ) as error:
                    print(
                        f"[LEVEL ROLE] {error}"
                    )
        await check_achievements(
            guild_id=message.guild.id,
            user_id=message.author.id,
        )

    # =========================================================
    # VOICE HELPERS
    # =========================================================

    async def save_voice_session(
        self,
        guild_id: int,
        user_id: int,
    ) -> int:
        """
        Сохраняет накопившуюся часть
        активной voice-сессии.

        Возвращает количество секунд,
        записанных в БД.
        """

        key = (
            guild_id,
            user_id,
        )

        started_at = (
            self.voice_sessions.get(
                key
            )
        )

        if started_at is None:
            return 0

        now = time.monotonic()

        seconds = int(
            now - started_at
        )

        if seconds <= 0:
            return 0

        # Сначала записываем в БД.
        #
        # Только после успешной записи
        # двигаем начало несохранённого
        # участка вперёд.
        (
            xp_gain,
            cases_gained,
            new_level,
        ) = await add_voice_seconds(
            guild_id=guild_id,
            user_id=user_id,
            seconds=seconds,
        )
        if cases_gained > 0:
            guild = self.bot.get_guild(
                guild_id
            )

            if guild is not None:
                member = guild.get_member(
                    user_id
                )

                if member is not None:
                    try:
                        await sync_level_role(
                            member=member,
                            level=new_level,
                        )
                    except (
                        discord.HTTPException,
                        RuntimeError,
                    ) as error:
                        print(
                            f"[LEVEL ROLE] {error}"
                        )
        await check_achievements(
            guild_id=guild_id,
            user_id=user_id,
        )
        # Не ставим просто `now`.
        #
        # Например:
        #
        # прошло 60.8 секунд
        # сохранили 60
        #
        # оставшиеся 0.8 секунды
        # не должны потеряться.
        self.voice_sessions[
            key
        ] = (
            started_at
            + seconds
        )

        return seconds

    # =========================================================
    # VOICE STATE
    # =========================================================

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        # Mute / deaf / stream и другие
        # изменения внутри того же канала
        # нас не интересуют.
        if (
            before.channel
            == after.channel
        ):
            return

        key = (
            member.guild.id,
            member.id,
        )

        # =====================================================
        # ENTER
        # =====================================================

        if (
            before.channel is None
            and after.channel is not None
        ):
            self.voice_sessions[
                key
            ] = time.monotonic()

            return

        # =====================================================
        # EXIT
        # =====================================================

        if (
            before.channel is not None
            and after.channel is None
        ):
            try:
                await self.save_voice_session(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )

            finally:
                # Даже если сохранение завершилось
                # ошибкой, нельзя оставлять
                # пользователя как будто он
                # продолжает сидеть в voice.
                self.voice_sessions.pop(
                    key,
                    None,
                )

            return

        # =====================================================
        # MOVE BETWEEN CHANNELS
        # =====================================================

        if (
            before.channel is not None
            and after.channel is not None
        ):
            # Для общей статистики voice
            # переход между каналами
            # не заканчивает сессию.
            #
            # Счётчик продолжает идти.
            if key not in self.voice_sessions:
                self.voice_sessions[
                    key
                ] = time.monotonic()

            return

    # =========================================================
    # PERIODIC VOICE SAVE
    # =========================================================

    @tasks.loop(
        seconds=VOICE_SAVE_INTERVAL
    )
    async def voice_save_loop(
        self,
    ) -> None:
        """
        Периодически сохраняет активные
        voice-сессии.

        Благодаря этому при аварийном
        завершении процесса не пропадает
        вся текущая сессия целиком.
        """

        # Копируем список ключей,
        # потому что callbacks Discord
        # могут менять словарь одновременно.
        active_sessions = list(
            self.voice_sessions.keys()
        )

        for (
            guild_id,
            user_id,
        ) in active_sessions:

            guild = self.bot.get_guild(
                guild_id
            )

            if guild is None:
                self.voice_sessions.pop(
                    (
                        guild_id,
                        user_id,
                    ),
                    None,
                )

                continue

            member = guild.get_member(
                user_id
            )

            # Если состояние Discord говорит,
            # что пользователь уже не в voice,
            # stale-сессию удаляем.
            if (
                member is None
                or member.voice is None
                or member.voice.channel is None
            ):
                self.voice_sessions.pop(
                    (
                        guild_id,
                        user_id,
                    ),
                    None,
                )

                continue

            await self.save_voice_session(
                guild_id=guild_id,
                user_id=user_id,
            )

    # =========================================================
    # BEFORE LOOP
    # =========================================================

    @voice_save_loop.before_loop
    async def before_voice_save_loop(
        self,
    ) -> None:
        await self.bot.wait_until_ready()

        await self.initialize_current_state()


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        Activity(bot)
    )