import discord
from utils.profile_card import (
    ProfileStats,
    create_profile_card
)
from discord import app_commands
from discord.ext import commands
from config.theme import EDEN_GOLD
from views.info_view import ServerInfoView
from utils.server_banner import create_server_banner
from database.member_stats import get_member_stats

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="testbanner",
        description="Тест обновления баннера"
    )
    async def testbanner(
        self,
        interaction: discord.Interaction
    ):
        guild = interaction.guild

        if guild is None:
            return

        online_count = sum(
            1
            for member in guild.members
            if member.status != discord.Status.offline
            and not member.bot
        )

        member_count = sum(
            1
            for member in guild.members
            if not member.bot
        )

        banner = create_server_banner(
            online_count,
            member_count
        )

        await guild.edit(
            banner=banner,
            reason="Тест динамического баннера"
        )

        await interaction.response.send_message(
            f"Баннер обновлён: "
            f"{online_count} в саду / "
            f"{member_count} душ",
            ephemeral=True
        )

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
        if interaction.guild is None:
            await interaction.response.send_message(
                "Профиль доступен только на сервере.",
                ephemeral=True
            )
            return

        if user is None:
            user = interaction.user

        await interaction.response.defer()

        db_stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=user.id
        )

        print(db_stats)

        profile_stats = ProfileStats(
            # Пока тестовые, позже рассчитаем
            level=27,
            rank=12,
            total_xp=3423,
            xp_to_next_level=2577,

            # Уже реальные данные из SQLite
            currency=db_stats.currency,
            messages=db_stats.messages,
            voice_seconds=db_stats.voice_seconds
        )

        card = await create_profile_card(
            user,
            profile_stats
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