import discord
from discord import app_commands
from discord.ext import commands

from config.roles import LEVEL_ROLES
from database.member_stats import get_member_stats
from services.level_roles import sync_level_role
from utils.leveling import level_from_xp


class MilestoneRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="роль-уровня",
        description="Синхронизировать юбилейную роль участника",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def sync_member_role(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        if not LEVEL_ROLES:
            await interaction.followup.send(
                "Список юбилейных ролей пока не настроен.",
                ephemeral=True,
            )
            return

        stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )
        level = level_from_xp(stats.xp)

        role = await sync_level_role(
            member=user,
            level=level,
        )

        if role is None:
            text = (
                f"У {user.mention} пока нет доступной "
                "юбилейной роли."
            )
        else:
            text = (
                f"Роль {user.mention} синхронизирована: "
                f"**{role.name}**."
            )

        await interaction.followup.send(
            text,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MilestoneRoles(bot))
