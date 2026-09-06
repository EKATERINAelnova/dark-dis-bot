import discord

from discord import app_commands
from discord.ext import commands

from cogs.events.common import (
    fetch_activity_message,
    get_activity_for_command,
)

from services.activities import (
    Activity,
    change_activity_status,
    create_activity,
    get_activity_participants,
    get_open_activities,
    set_activity_message,
)

from views.activity.activity_view import (
    ActivityView,
    build_activity_embed,
)


class Closes(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    async def cog_load(
        self,
    ) -> None:
        activities = await get_open_activities(
            activity_type="close"
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

    async def refresh_close_message(
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
        name="создать-клоз",
        description="Создать закрытую игровую активность",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def create_close(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        max_participants: app_commands.Range[
            int,
            2,
            20,
        ] = 10,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer()

        try:
            activity = await create_activity(
                guild_id=interaction.guild.id,
                activity_type="close",
                title=title,
                description=description,
                host_id=interaction.user.id,
                max_participants=max_participants,
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

        message = None

        try:
            message = await interaction.followup.send(
                embed=build_activity_embed(
                    activity=activity,
                    participants=[],
                ),
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

            if message is not None:
                try:
                    await message.edit(
                        view=None
                    )
                except discord.HTTPException:
                    pass

            print(
                f"[CLOSE CREATE] {error}"
            )

            await interaction.followup.send(
                "Не удалось опубликовать CLOSE. Он отменён.",
                ephemeral=True,
            )

    @app_commands.command(
        name="запустить-клоз",
        description="Закрыть набор и запустить CLOSE",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def start_close(
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
            activity_type="close",
        )

        if activity is None:
            return

        participants = await get_activity_participants(
            activity_id=activity_id
        )

        if len(participants) < 2:
            await interaction.followup.send(
                "Для запуска CLOSE нужно минимум 2 участника.",
                ephemeral=True,
            )
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
                "Этот CLOSE уже нельзя запустить.",
                ephemeral=True,
            )
            return

        await self.refresh_close_message(
            activity
        )

        await interaction.followup.send(
            f"CLOSE **#{activity_id}** запущен. Набор закрыт.",
            ephemeral=True,
        )

    @app_commands.command(
        name="отменить-клоз",
        description="Отменить CLOSE",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def cancel_close(
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
            activity_type="close",
        )

        if activity is None:
            return

        if activity.status not in {
            "open",
            "running",
        }:
            await interaction.followup.send(
                "Этот CLOSE уже закрыт.",
                ephemeral=True,
            )
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
                "Не удалось отменить CLOSE.",
                ephemeral=True,
            )
            return

        await self.refresh_close_message(
            activity
        )

        await interaction.followup.send(
            f"CLOSE **#{activity_id}** отменён.",
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Closes(bot)
    )
