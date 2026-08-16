import discord

from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
    name="ping",
    description="Проверить работу бота"
    )
    async def ping(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message("Pong!")

    
    @app_commands.command(
        name="userinfo",
        description="Информация о пользователе"
    )
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member):
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

    @app_commands.command(
        name="serverinfo",
        description="Информация о сервере"
    )
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        msg = (f"Название:  {guild.name} \n"
        f"Id: {str(guild.id)} \n"
        f"Участников: {str(guild.member_count)} \n"
        f"Владелец: {(guild.owner.mention)}")
        await interaction.response.send_message(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))