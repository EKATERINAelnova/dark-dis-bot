import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database.connection import init_db
from database.member_stats import ensure_members_exist


load_dotenv()

TOKEN = os.getenv("DIS_TOKEN")
GID = os.getenv("GUILD_ID")


class BotClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()

        intents.members = True
        intents.presences = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await init_db()

        await self.load_extension(
            "cogs.general.general"
        )
        await self.load_extension(
            "cogs.fun.fun"
        )
        await self.load_extension(
            "cogs.activity"
        )
        await self.load_extension(
            "cogs.welcome.banner"
        )
        await self.load_extension(
            "cogs.moderation.economy_admin"
        )

        guild = discord.Object(
            id=int(GID)
        )

        self.tree.copy_global_to(
            guild=guild
        )

        synced = await self.tree.sync(
            guild=guild
        )

        print(
            f"Синхронизировано команд: "
            f"{len(synced)}"
        )


client = BotClient()


@client.event
async def on_ready():
    print(f"Бот запущен: {client.user}")

    for guild in client.guilds:
        member_ids = [
            member.id
            for member in guild.members
            if not member.bot
        ]

        await ensure_members_exist(
            guild_id=guild.id,
            user_ids=member_ids,
        )

        print(
            f"[DB] Синхронизировано участников "
            f"{guild.name}: {len(member_ids)}"
        )


client.run(TOKEN)