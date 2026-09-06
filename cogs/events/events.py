import discord

from discord import app_commands
from discord.ext import commands

from cogs.events.common import (
    fetch_activity_message,
    get_activity_for_command,
)

from cogs.events.reward_helpers import (
    format_reward,
    process_xp_rewards,
)

from services.activities import (
    Activity,
    change_activity_status,
    create_activity,
    get_activity_participants,
    get_open_activities,
    set_activity_message,
)

from services.activity_rewards import (
    reward_activity_participants,
)

from services.automatic_activity_rewards import (
    reward_event_automatically,
)

from views.activity.activity_view import (
    ActivityView,
    build_activity_embed,
)


class Events(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    async def cog_load(
        self,
    ) -> None:
        await self.restore_open_events()

    async def restore_open_events(
        self,
    ) -> None:
        activities = await get_open_activities(
            activity_type="event"
        )

        for activity in activities:
            if activity.message_id is None:
                continue

            self.bot.add_view(
                ActivityView(
                    activity_id=activity.activity_id
                ),
                message_id=activity.message_id,
            )

    async def refresh_activity_message(
        self,
        activity: Activity,
    ) -> None:
        message = await fetch_activity_message(
            self.bot,
            activity,
        )

        if message is None:
            return

        participants = (
            await get_activity_participants(
                activity_id=activity.activity_id
            )
        )

        view = ActivityView(
            activity_id=activity.activity_id
        )

        if activity.status != "open":
            view.disable_buttons()

        await message.edit(
            embed=build_activity_embed(
                activity,
                participants,
            ),
            view=view,
        )

    @app_commands.command(
        name="event-create",
        description="Создать серверный ивент",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.choices(
        reward=[
            app_commands.Choice(
                name="SMALL · 20 🍎 + 15 XP",
                value="small",
            ),
            app_commands.Choice(
                name="EVENT · 40 🍎 + 30 XP",
                value="standard",
            ),
            app_commands.Choice(
                name="MAJOR · 75 🍎 + 50 XP + 1 CASE",
                value="major",
            ),
        ]
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        reward: app_commands.Choice[str],
        max_participants: app_commands.Range[
            int,
            1,
            100,
        ] = 20,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer()

        try:
            activity = await create_activity(
                guild_id=interaction.guild.id,
                activity_type="event",
                title=title,
                description=description,
                host_id=interaction.user.id,
                max_participants=max_participants,
                reward_preset=reward.value,
            )

        except ValueError as error:
            await interaction.followup.send(
                str(error),
                ephemeral=True,
            )
            return

        view = ActivityView(
            activity_id=activity.activity_id
        )

        embed = build_activity_embed(
            activity=activity,
            participants=[],
        )

        try:
            message = await interaction.followup.send(
                embed=embed,
                view=view,
                wait=True,
            )

            await set_activity_message(
                guild_id=interaction.guild.id,
                activity_id=activity.activity_id,
                channel_id=message.channel.id,
                message_id=message.id,
            )

        except Exception as error:
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity.activity_id,
                new_status="cancelled",
            )

            print(
                f"[EVENT CREATE] {error}"
            )

            await interaction.followup.send(
                (
                    "Не удалось опубликовать EVENT. "
                    "Он был отменён."
                ),
                ephemeral=True,
            )

    @app_commands.command(
        name="event-start",
        description="Запустить серверный ивент",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def start_event(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="event",
        )

        if activity is None:
            return

        status, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="running",
            )
        )

        if (
            status != "changed"
            or activity is None
        ):
            await interaction.followup.send(
                "Этот EVENT уже нельзя запустить.",
                ephemeral=True,
            )
            return

        await self.refresh_activity_message(
            activity
        )

        await interaction.followup.send(
            f"EVENT **#{activity_id}** запущен.",
            ephemeral=True,
        )

    @app_commands.command(
        name="event-finish",
        description="Завершить серверный ивент",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def finish_event(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="event",
        )

        if activity is None:
            return

        status, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="finished",
            )
        )

        if (
            status != "changed"
            or activity is None
        ):
            await interaction.followup.send(
                "Сначала EVENT должен быть запущен.",
                ephemeral=True,
            )
            return

        reward_results = []

        try:
            reward_results = (
                await reward_event_automatically(
                    activity=activity,
                    actor_id=interaction.user.id,
                )
            )

            await process_xp_rewards(
                guild=interaction.guild,
                results=reward_results,
            )

        except Exception as error:
            print(
                f"[EVENT AUTO REWARD] {error}"
            )

        await self.refresh_activity_message(
            activity
        )

        granted_users = {
            result.user_id
            for result in reward_results
            if result.status == "granted"
        }

        text = (
            f"EVENT **#{activity_id}** завершён."
        )

        if granted_users:
            text += (
                f"\nНаграды автоматически получили: "
                f"**{len(granted_users)}**."
            )
        elif reward_results:
            text += (
                "\nАвтоматические награды уже были выданы."
            )
        else:
            text += (
                "\nУчастников для награждения нет."
            )

        await interaction.followup.send(
            text,
            ephemeral=True,
        )

    @app_commands.command(
        name="event-cancel",
        description="Отменить серверный ивент",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def cancel_event(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="event",
        )

        if activity is None:
            return

        status, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="cancelled",
            )
        )

        if (
            status != "changed"
            or activity is None
        ):
            await interaction.followup.send(
                "Этот EVENT уже завершён или отменён.",
                ephemeral=True,
            )
            return

        await self.refresh_activity_message(
            activity
        )

        await interaction.followup.send(
            f"EVENT **#{activity_id}** отменён.",
            ephemeral=True,
        )

    @app_commands.command(
        name="event-reward",
        description="Дополнительно наградить участников ивента",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.choices(
        reward_kind=[
            app_commands.Choice(
                name="Средства",
                value="currency",
            ),
            app_commands.Choice(
                name="XP",
                value="xp",
            ),
            app_commands.Choice(
                name="EDEN CASE",
                value="case",
            ),
        ]
    )
    async def reward_event(
        self,
        interaction: discord.Interaction,
        activity_id: int,
        reward_kind: app_commands.Choice[str],
        amount: app_commands.Range[
            int,
            1,
            10000,
        ],
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(
            ephemeral=True
        )

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="event",
        )

        if activity is None:
            return

        if activity.status != "finished":
            await interaction.followup.send(
                (
                    "Дополнительную награду можно выдать "
                    "только после завершения EVENT."
                ),
                ephemeral=True,
            )
            return

        kind = reward_kind.value

        if kind == "case" and amount > 10:
            await interaction.followup.send(
                "Нельзя выдать больше 10 EDEN CASE.",
                ephemeral=True,
            )
            return

        results = await reward_activity_participants(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            reward_kind=kind,
            amount=amount,
            actor_id=interaction.user.id,
            reward_prefix="manual",
        )

        if not results:
            await interaction.followup.send(
                "У этого EVENT нет участников.",
                ephemeral=True,
            )
            return

        granted = [
            result
            for result in results
            if result.status == "granted"
        ]

        if kind == "xp":
            await process_xp_rewards(
                guild=interaction.guild,
                results=granted,
            )

        reward_text = format_reward(
            kind=kind,
            amount=amount,
        )

        if not granted:
            await interaction.followup.send(
                (
                    f"Дополнительная награда "
                    f"**{reward_text}** уже выдавалась."
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            (
                f"Дополнительно выдано **{reward_text}**.\n"
                f"Получили: **{len(granted)}**."
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Events(bot)
    )
