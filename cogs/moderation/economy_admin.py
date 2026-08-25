import discord

from discord import app_commands
from discord.ext import commands
from database.member_stats import add_xp, get_member_stats
from services.level_roles import sync_level_role
from utils.leveling import level_from_xp

from config.economy import (
    CURRENCY_SYMBOL,
    REASON_ADMIN,
)

from database.economy import change_balance

from utils.embeds import (
    success_embed,
    error_embed,
)


class EconomyAdmin(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    # =========================================================
    # ADD FUNDS
    # =========================================================

    @app_commands.command(
        name="addxp",
        description="Добавить XP пользователю для теста",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def add_xp_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[int, 1, 1000000],
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        new_xp, new_level, cases_gained = await add_xp(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=amount,
        )

        if cases_gained > 0:
            await sync_level_role(
                member=user,
                level=new_level,
            )

        if cases_gained > 0:
            reward_text = (
                f"\n\n✦ Получено EDEN CASE: "
                f"**{cases_gained}**"
            )
        else:
            reward_text = ""

        await interaction.followup.send(
            (
                f"Добавлено **{amount} XP** "
                f"для {user.mention}.\n\n"
                f"XP: **{new_xp}**\n"
                f"Уровень: **{new_level}**"
                f"{reward_text}"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="addfunds",
        description="Добавить средства пользователю",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def add_funds(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[
            int,
            1,
            100000,
        ],
    ) -> None:
        if interaction.guild is None:
            return

        new_balance = await change_balance(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=amount,
            reason=REASON_ADMIN,
            description="admin_add",
            actor_id=interaction.user.id,
        )

        embed = success_embed(
            title="Баланс изменён",
            description=(
                f"Баланс {user.mention} увеличен "
                f"на **{amount} {CURRENCY_SYMBOL}**.\n\n"
                f"Новый баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @app_commands.command(
        name="synclevelrole",
        description="Обновить level-роль пользователя",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def sync_level_role_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        stats = await get_member_stats(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        level = level_from_xp(
            stats.xp
        )

        role = await sync_level_role(
            member=user,
            level=level,
        )

        if role is None:
            text = (
                f"{user.mention} сейчас "
                f"на **{level} уровне**.\n"
                "Юбилейная роль пока не положена."
            )
        else:
            text = (
                f"{user.mention}\n"
                f"Уровень: **{level}**\n"
                f"Роль: **{role.name}**"
            )

        await interaction.followup.send(
            text,
            ephemeral=True,
        )

    # =========================================================
    # REMOVE FUNDS
    # =========================================================

    @app_commands.command(
        name="removefunds",
        description="Уменьшить средства пользователя",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def remove_funds(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: app_commands.Range[
            int,
            1,
            100000,
        ],
    ) -> None:
        if interaction.guild is None:
            return

        new_balance = await change_balance(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=-amount,
            reason=REASON_ADMIN,
            description="admin_remove",
            actor_id=interaction.user.id,
        )

        # =====================================================
        # INSUFFICIENT FUNDS
        # =====================================================

        if new_balance is None:
            embed = error_embed(
                title="Недостаточно средств",
                description=(
                    f"На балансе {user.mention} "
                    f"недостаточно средств.\n\n"
                    f"Нельзя списать "
                    f"**{amount} {CURRENCY_SYMBOL}**."
                ),
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

            return

        # =====================================================
        # SUCCESS
        # =====================================================

        embed = success_embed(
            title="Баланс изменён",
            description=(
                f"Баланс {user.mention} уменьшен "
                f"на **{amount} {CURRENCY_SYMBOL}**.\n\n"
                f"Новый баланс: "
                f"**{new_balance} {CURRENCY_SYMBOL}**"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    await bot.add_cog(
        EconomyAdmin(bot)
    )