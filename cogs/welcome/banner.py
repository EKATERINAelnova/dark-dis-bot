import discord

from discord.ext import commands, tasks

from utils.server_banner import create_server_banner


class Banner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.last_counts: dict[int, tuple[int, int]] = {}

    async def cog_load(self):
        self.update_banner.start()

    async def cog_unload(self):
        self.update_banner.cancel()

    @tasks.loop(seconds=10)
    async def update_banner(self):
        for guild in self.bot.guilds:

            try:
                await self.update_guild_banner(guild)

            except Exception as error:
                print(
                    f"[BANNER] Неожиданная ошибка "
                    f"на сервере {guild.name}: {error}"
                )

    async def update_guild_banner(
        self,
        guild: discord.Guild
    ):
        if "BANNER" not in guild.features:
            return

        bot_member = guild.me

        if bot_member is None:
            return

        if not bot_member.guild_permissions.manage_guild:
            return

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

        counts = (
            online_count,
            member_count
        )

        if self.last_counts.get(guild.id) == counts:
            return

        banner = create_server_banner(
            online_count=online_count,
            member_count=member_count
        )

        try:
            await guild.edit(
                banner=banner,
                reason="Обновление счётчика LOST EDEN"
            )

        except discord.Forbidden:
            print(
                f"[BANNER] {guild.name}: "
                "нет прав на изменение баннера"
            )
            return

        except discord.HTTPException as error:
            print(
                f"[BANNER] {guild.name}: "
                f"ошибка Discord API: {error}"
            )
            return

        self.last_counts[guild.id] = counts

        print(
            f"[BANNER] {guild.name}: "
            f"{online_count} в саду / "
            f"{member_count} душ"
        )

    @update_banner.before_loop
    async def before_update_banner(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Banner(bot))