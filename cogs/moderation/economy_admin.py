import discord

from discord import app_commands
from discord.ext import commands

from config.economy import (
    CURRENCY_SYMBOL,
    REASON_ADMIN,
)
from database.economy import change_balance
from database.member_stats import (
    add_xp,
    get_member_stats,
)
from services.achievements import check_achievements
from services.level_roles import sync_level_role
from services.reward_processing import process_xp_rewards
from services.reward_recovery import retry_activity_rewards
from utils.embeds import (
    error_embed,
    success_embed,
)
from utils.leveling import level_from_xp


class EconomyAdmin(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="добавить-опыт",
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
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        new_xp, new_level, cases_gained = await add_xp(
            guild_id=interaction.guild.id,
            user_id=user.id,
            amount=amount,
        )

        await check_achievements(
            guild_id=interaction.guild.id,
            user_id=user.id,
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
        name="добавить-средства",
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
        name="обновить-роль-уровня",
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
        if interaction.guild is None:
            return

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

    @app_commands.command(
        name="повторить-награды",
        description="Повторить автоматическую выдачу наград активности",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def retry_rewards(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ) -> None:
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        recovery = await retry_activity_rewards(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            actor_id=interaction.user.id,
        )

        error_messages = {
            "not_found": "Активность не найдена.",
            "not_finished": "Сначала активность должна быть завершена.",
            "result_not_confirmed": (
                "Результат этой активности ещё не подтверждён."
            ),
            "unsupported_type": (
                "Для этого типа активности автоматические награды "
                "не поддерживаются."
            ),
        }

        if recovery.status != "processed":
            await interaction.followup.send(
                error_messages.get(
                    recovery.status,
                    "Не удалось повторить выдачу наград.",
                ),
                ephemeral=True,
            )
            return

        await process_xp_rewards(
            guild=interaction.guild,
            results=recovery.rewards,
        )

        granted = sum(
            result.status == "granted"
            for result in recovery.rewards
        )

        already_granted = sum(
            result.status == "already_granted"
            for result in recovery.rewards
        )

        skipped = (
            len(recovery.rewards)
            - granted
            - already_granted
        )

        await interaction.followup.send(
            (
                f"Награды активности **#{activity_id}** проверены.\n\n"
                f"Выдано сейчас: **{granted}**\n"
                f"Уже было выдано: **{already_granted}**\n"
                f"Не положено по правилам: **{skipped}**"
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="снять-средства",
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
