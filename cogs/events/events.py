import discord

from discord import app_commands
from discord.ext import commands

from services.activities import (
    Activity,
    change_activity_status,
    create_activity,
    get_activity,
    get_activity_participants,
    get_open_activities,
    set_activity_message,
)

from views.activity_view import (
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
        activities = await get_open_activities()

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
        if (
            activity.channel_id is None
            or activity.message_id is None
        ):
            return

        channel = self.bot.get_channel(
            activity.channel_id
        )

        if channel is None:
            return

        if not hasattr(
            channel,
            "fetch_message",
        ):
            return

        try:
            message = await channel.fetch_message(
                activity.message_id
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
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
    async def create_event(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        max_participants: app_commands.Range[
            int,
            1,
            100,
        ] = 20,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer()

        activity = await create_activity(
            guild_id=interaction.guild.id,
            activity_type="event",
            title=title,
            description=description,
            host_id=interaction.user.id,
            max_participants=max_participants,
        )

        view = ActivityView(
            activity_id=activity.activity_id
        )

        embed = build_activity_embed(
            activity=activity,
            participants=[],
        )

        await interaction.followup.send(
            embed=embed,
            view=view,
        )

        message = (
            await interaction.original_response()
        )

        await set_activity_message(
            guild_id=interaction.guild.id,
            activity_id=activity.activity_id,
            channel_id=message.channel.id,
            message_id=message.id,
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

        activity = await get_activity(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
        )

        if (
            activity is None
            or activity.type != "event"
        ):
            await interaction.followup.send(
                "Такой EVENT не найден.",
                ephemeral=True,
            )
            return

        result, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="running",
            )
        )

        if (
            result != "changed"
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

        activity = await get_activity(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
        )

        if (
            activity is None
            or activity.type != "event"
        ):
            await interaction.followup.send(
                "Такой EVENT не найден.",
                ephemeral=True,
            )
            return

        result, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="finished",
            )
        )

        if (
            result != "changed"
            or activity is None
        ):
            await interaction.followup.send(
                "Сначала EVENT должен быть запущен.",
                ephemeral=True,
            )
            return

        await self.refresh_activity_message(
            activity
        )

        await interaction.followup.send(
            f"EVENT **#{activity_id}** завершён.",
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

        activity = await get_activity(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
        )

        if (
            activity is None
            or activity.type != "event"
        ):
            await interaction.followup.send(
                "Такой EVENT не найден.",
                ephemeral=True,
            )
            return

        result, activity = (
            await change_activity_status(
                guild_id=interaction.guild.id,
                activity_id=activity_id,
                new_status="cancelled",
            )
        )

        if (
            result != "changed"
            or activity is None
        ):
            await interaction.followup.send(
                (
                    "Этот EVENT уже завершён "
                    "или отменён."
                ),
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


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Events(bot)
    )