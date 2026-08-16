import discord

from discord import app_commands
from discord.ext import commands
from config.theme import EDEN_GOLD
from .views.info_view import ServerInfoView

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
    description="Информация об участнике сада"
)
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        if user.joined_at is None:
            joined_text = "Неизвестно"
        else:
            joined_text = user.joined_at.strftime("%d.%m.%Y")

        created_text = user.created_at.strftime("%d.%m.%Y")

        roles_text = ", ".join(
            role.mention
            for role in user.roles
            if role.name != "@everyone"
        )

        if roles_text == "":
            roles_text = "Пока без выбранных ролей"

        embed = discord.Embed(
            title="🌿 Путник сада",
            description=(
                f"{user.mention}\n"
                "*Каждый приходит сюда со своей дорогой за спиной.*"
            ),
            colour=EDEN_GOLD
        )

        embed.add_field(
            name="Имя",
            value=user.display_name,
            inline=True
        )

        embed.add_field(
            name="В саду с",
            value=joined_text,
            inline=True
        )

        embed.add_field(
            name="Путь начался",
            value=created_text,
            inline=True
        )

        embed.add_field(
            name="Корни и состояния",
            value=roles_text,
            inline=False
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.set_footer(
            text=f"LOST EDEN · RIMAY  •  ID {user.id}"
        )

        await interaction.response.send_message(
            embed=embed
        )

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