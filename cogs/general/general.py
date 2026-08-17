import discord
from utils.profile_card import (
    ProfileStats,
    create_profile_card
)
from discord import app_commands
from discord.ext import commands
from config.theme import EDEN_GOLD
from views.info_view import ServerInfoView

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
        name="profile",
        description="Открыть профиль участника сада"
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None
    ):
        if user is None:
            user = interaction.user

        await interaction.response.defer()
        stats = ProfileStats(
            level=27,
            rank=12,
            currency=1480,
            messages=4362,
            voice_seconds=462840,
            total_xp=3423,
            xp_to_next_level=2577
        )

        card = await create_profile_card(
            user,
            stats
        )

        file = discord.File(
            card,
            filename="profile.png"
        )

        await interaction.followup.send(
            file=file
        )
    
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
    description="Открыть карту LOST EDEN"
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Карта сада доступна только внутри сервера.",
                ephemeral=True
            )
            return

        view = ServerInfoView(
            guild=guild,
            user_id=interaction.user.id
        )

        await interaction.response.send_message(
            embed=view.main_embed(),
            view=view
        )

        view.message = await interaction.original_response()

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))