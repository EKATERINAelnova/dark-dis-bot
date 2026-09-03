import discord

from discord import app_commands
from discord.ext import commands

from services.activities import (
    Activity,
    change_activity_status,
    get_activity,
    get_open_activities,
    set_activity_message,
)

from services.duels import (
    create_duel,
    get_duel_players,
)

from views.activity.duel_view import (
    DuelView,
    build_duel_embed,
)


class Duels(commands.Cog):
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
            if activity.type != "duel":
                continue

            if activity.message_id is None:
                continue

            players = await get_duel_players(
                activity.activity_id
            )

            if players is None:
                continue

            challenger_id, opponent_id = players

            self.bot.add_view(
                DuelView(
                    activity_id=activity.activity_id,
                    challenger_id=challenger_id,
                    opponent_id=opponent_id,
                ),
                message_id=activity.message_id,
            )

    async def refresh_duel_message(
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

        players = await get_duel_players(
            activity.activity_id
        )

        if players is None:
            return

        challenger_id, opponent_id = players

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

        view = None

        if activity.status == "open":
            view = DuelView(
                activity_id=activity.activity_id,
                challenger_id=challenger_id,
                opponent_id=opponent_id,
            )

        await message.edit(
            content=None,
            embed=build_duel_embed(
                activity=activity,
                challenger_id=challenger_id,
                opponent_id=opponent_id,
            ),
            view=view,
        )

    @app_commands.command(
        name="duel",
        description="Бросить вызов участнику сада",
    )
    @app_commands.guild_only()
    async def duel(
        self,
        interaction: discord.Interaction,
        opponent: discord.Member,
    ):
        if interaction.guild is None:
            return

        if opponent.bot:
            await interaction.response.send_message(
                "Ботов на дуэль не вызываем.",
                ephemeral=True,
            )
            return

        if opponent.id == interaction.user.id:
            await interaction.response.send_message(
                "С самим собой дуэль не получится.",
                ephemeral=True,
            )
            return

        channel = interaction.channel

        if (
            channel is None
            or not hasattr(
                channel,
                "send",
            )
        ):
            await interaction.response.send_message(
                (
                    "В этом канале нельзя "
                    "создать DUEL."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        challenger_name = getattr(
            interaction.user,
            "display_name",
            interaction.user.name,
        )

        title = (
            f"{challenger_name} "
            f"VS "
            f"{opponent.display_name}"
        )

        result = await create_duel(
            guild_id=interaction.guild.id,
            challenger_id=interaction.user.id,
            opponent_id=opponent.id,
            title=title,
        )

        if result.status == "challenger_busy":
            await interaction.followup.send(
                (
                    "У тебя уже есть "
                    "незавершённая дуэль."
                ),
                ephemeral=True,
            )
            return

        if result.status == "opponent_busy":
            await interaction.followup.send(
                (
                    f"{opponent.mention} уже "
                    f"участвует в другой дуэли."
                ),
                ephemeral=True,
            )
            return

        if (
            result.status != "created"
            or result.activity is None
        ):
            await interaction.followup.send(
                "Не удалось создать DUEL.",
                ephemeral=True,
            )
            return

        activity = result.activity

        view = DuelView(
            activity_id=activity.activity_id,
            challenger_id=interaction.user.id,
            opponent_id=opponent.id,
        )

        embed = build_duel_embed(
            activity=activity,
            challenger_id=interaction.user.id,
            opponent_id=opponent.id,
        )

        message = None

        try:
            message = await channel.send(
                content=opponent.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    users=[
                        opponent
                    ]
                ),
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
                f"[DUEL CREATE] {error}"
            )

            await interaction.followup.send(
                (
                    "Не удалось опубликовать "
                    "DUEL. Вызов отменён."
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            (
                f"DUEL **#{activity.activity_id}** "
                f"создан."
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="duel-cancel",
        description="Принудительно закрыть дуэль",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def cancel_duel(
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
            or activity.type != "duel"
        ):
            await interaction.followup.send(
                "Такой DUEL не найден.",
                ephemeral=True,
            )
            return

        if activity.status not in {
            "open",
            "running",
        }:
            await interaction.followup.send(
                "Этот DUEL уже закрыт.",
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
                "Не удалось закрыть DUEL.",
                ephemeral=True,
            )
            return

        await self.refresh_duel_message(
            activity
        )

        await interaction.followup.send(
            (
                f"DUEL **#{activity_id}** "
                f"закрыт."
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        Duels(bot)
    )