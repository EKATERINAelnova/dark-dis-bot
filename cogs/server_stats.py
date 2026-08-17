#файл для теста

import os

import discord
from discord.ext import commands, tasks

stats_channel_id = os.getenv("STATS_CHANNEL_ID")

if stats_channel_id is None:
    raise RuntimeError(
        "STATS_CHANNEL_ID не найден в .env"
    )

STATS_CHANNEL_ID = int(stats_channel_id)


class ServerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.stats_message: discord.Message | None = None
        self.last_content: str | None = None

    async def cog_load(self):
        print("[STATS] Cog загружен")
        self.update_stats.start()

    async def cog_unload(self):
        print("[STATS] Cog выгружен")
        self.update_stats.cancel()

    @tasks.loop(seconds=10)
    async def update_stats(self):
        print("[STATS] Проверка...")

        channel = self.bot.get_channel(
            STATS_CHANNEL_ID
        )

        if channel is None:
            print(
                f"[STATS] Канал "
                f"{STATS_CHANNEL_ID} не найден"
            )
            return

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            print(
                "[STATS] STATS_CHANNEL_ID "
                "должен указывать на текстовый канал"
            )
            return

        guild = channel.guild

        online_count = sum(
            1
            for member in guild.members
            if not member.bot
            and member.status != discord.Status.offline
        )

        member_count = sum(
            1
            for member in guild.members
            if not member.bot
        )

        content = (
            f"В сети: {online_count}\n"
            f"Участников: {member_count}"
        )

        print(
            f"[STATS] online={online_count}, "
            f"members={member_count}"
        )

        # Сообщения пока нет.
        # Создаём его один раз.
        if self.stats_message is None:
            try:
                self.stats_message = await channel.send(
                    content
                )

                self.last_content = content

                print(
                    "[STATS] Создано сообщение "
                    f"id={self.stats_message.id}"
                )

            except discord.Forbidden:
                print(
                    "[STATS] Нет прав "
                    "на отправку сообщений"
                )

            except discord.HTTPException as error:
                print(
                    f"[STATS] Ошибка Discord API: "
                    f"{error}"
                )

            return

        # Ничего не изменилось.
        if self.last_content == content:
            print(
                "[STATS] Значения не изменились"
            )
            return

        print(
            "[STATS] Значения изменились, "
            "редактирую сообщение..."
        )

        try:
            self.stats_message = (
                await self.stats_message.edit(
                    content=content
                )
            )

        except discord.NotFound:
            # Например, сообщение удалили вручную.
            print(
                "[STATS] Старое сообщение удалено, "
                "создаю новое"
            )

            self.stats_message = await channel.send(
                content
            )

        except discord.Forbidden:
            print(
                "[STATS] Нет прав "
                "на изменение сообщения"
            )
            return

        except discord.HTTPException as error:
            print(
                f"[STATS] Ошибка Discord API: "
                f"{error}"
            )
            return

        self.last_content = content

        print(
            "[STATS] Сообщение обновлено"
        )

    @update_stats.before_loop
    async def before_update_stats(self):
        print(
            "[STATS] Жду готовности бота..."
        )

        await self.bot.wait_until_ready()

        print(
            "[STATS] Loop запущен"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        ServerStats(bot)
    )