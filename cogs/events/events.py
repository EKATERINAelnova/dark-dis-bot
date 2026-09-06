import discord

from discord import app_commands
from discord.ext import commands

from cogs.events.common import (
    fetch_activity_message,
    get_activity_for_command,
)

from cogs.events.reward_helpers import (
    encode_custom_event_reward,
    format_reward,
    process_xp_rewards,
)

from config.economy import (
    EVENT_MAX_CASE_REWARD,
    EVENT_MAX_CURRENCY_REWARD,
    EVENT_MAX_XP_REWARD,
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

        participants = await get_activity_participants(
            activity_id=activity.activity_id
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
        name="создать-ивент",
        description="Создать серверный ивент",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        currency: app_commands.Range[
            int,
            0,
            EVENT_MAX_CURRENCY_REWARD,
        ] = 0,
        xp: app_commands.Range[
            int,
            0,
            EVENT_MAX_XP_REWARD,
        ] = 0,
        cases: app_commands.Range[
            int,
            0,
            EVENT_MAX_CASE_REWARD,
        ] = 0,
        max_participants: app_commands.Range[
            int,
            1,
            100,
        ] = 20,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer()

        reward_value = encode_custom_event_reward(
            currency=currency,
            xp=xp,
            cases=cases,
        )

        try:
            activity = await create_activity(
                guild_id=interaction.guild.id,
                activity_type="event",
                title=title,
                description=description,
                host_id=interaction.user.id,
                max_participants=max_participants,
                reward_preset=reward_value,
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
                "Не удалось опубликовать EVENT. Он отменён.",
                ephemeral=True,
            )

    @app_commands.command(
        name="запустить-ивент",
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

        status, activity = await change_activity_status(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            new_status="running",
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
        name="завершить-ивент",
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

        status, activity = await change_activity_status(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            new_status="finished",
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
        reward_error = None

        try:
            reward_results = await reward_event_automatically(
                activity=activity,
                actor_id=interaction.user.id,
            )

            await process_xp_rewards(
                guild=interaction.guild,
                results=reward_results,
            )

        except Exception as error:
            reward_error = error
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

        text = f"EVENT **#{activity_id}** завершён."

        if reward_error is not None:
            text += "\nАвтоматическая награда не выдалась."
        elif granted_users:
            text += (
                f"\nНаграды получили: "
                f"**{len(granted_users)}**."
            )
        elif reward_results:
            text += "\nНаграды уже были выданы."
        else:
            text += "\nНаграждать некого или награда нулевая."

        await interaction.followup.send(
            text,
            ephemeral=True,
        )

    @app_commands.command(
        name="отменить-ивент",
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

        status, activity = await change_activity_status(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            new_status="cancelled",
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
        name="награда-ивента",
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
            500,
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
                "Дополнительная награда доступна после EVENT.",
                ephemeral=True,
            )
            return

        kind = reward_kind.value

        if (
            kind == "case"
            and amount > EVENT_MAX_CASE_REWARD
        ):
            await interaction.followup.send(
                (
                    f"Нельзя выдать больше "
                    f"{EVENT_MAX_CASE_REWARD} EDEN CASE."
                ),
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
                f"Награда **{reward_text}** уже выдавалась.",
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