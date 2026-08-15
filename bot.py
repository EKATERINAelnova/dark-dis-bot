import os
import random

import discord
from discord import app_commands
from dotenv import load_dotenv
from coin_view import CoinView

load_dotenv()

TOKEN = os.getenv("DIS_TOKEN")


class BotClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=1212134682234196019)

        self.tree.copy_global_to(guild=guild)

        synced = await self.tree.sync(guild=guild)

        print(f"Синхронизировано команд: {len(synced)}")


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

@client.tree.command(
    name="userinfo",
    description="Информация о пользователе"
)
async def userinfo(interaction: discord.Interaction, user: discord.Member):
    embed = discord.Embed(
        title="Информация о юзере",
        description=user.mention,
        colour=user.colour
    )
    if user.joined_at is None:
        joined_text = "Неизвестно"
    else:
        joined_text = user.joined_at.strftime("%d.%m.%Y %H:%M")

    if user.joined_at is None:
        joined_ds = "Неизвестно"
    else:
        joined_ds = user.created_at.strftime("%d.%m.%Y %H:%M")

    rs = ", ".join(
        role.mention
        for role in user.roles
        if role.name != "@everyone"
    )
    if rs == "":
        rs ="Нет ролей"
    embed.add_field(name="Имя", value=user.name)
    embed.add_field(name="Отображаемое имя", value=user.display_name)
    embed.add_field(name="Id", value=user.id)
    embed.add_field(name="Дата входа на сервер", value=joined_text)
    embed.add_field(name="Аккаунт создан", value=joined_ds)
    embed.add_field(name="Роли", value=rs)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"Id user: {user.id}")
    await interaction.response.send_message(embed=embed)

@client.tree.command(
    name="serverinfo",
    description="Информация о сервере"
)
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    msg = (f"Название:  {guild.name} \n"
    f"Id: {str(guild.id)} \n"
    f"Участников: {str(guild.member_count)} \n"
    f"Владелец: {(guild.owner.mention)}")
    await interaction.response.send_message(msg)

@client.tree.command(
    name="roll",
    description="Бросить случайное число"
)
async def roll(
    interaction: discord.Interaction,
    max_value: app_commands.Range[int, 1, 1000]
):
    r = random.randint(1, max_value)
    await interaction.response.send_message(f"Выпало: {r}")

@client.tree.command(
    name="coin",
    description="Подбросить монетку"
)
async def coin(interaction: discord.Interaction):
    view = CoinView(interaction.user.id)

    await interaction.response.send_message(
        "Выбери сторону:",
        view=view
    )
    random.choice(["Орёл", "Решка"])


client.run(TOKEN)