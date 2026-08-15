import os

import discord
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DIS_TOKEN")


class BotClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


client = BotClient()


@client.event
async def on_ready():
    print(f"Бот запущен: {client.user}")


@client.tree.command(
    name="ping",
    description="Проверить работу бота"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


client.run(TOKEN)