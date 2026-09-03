import asyncio

import discord

from services.activities import (
    Activity,
    change_activity_status,
    get_activity,
)

from utils.embeds import (
    eden_embed,
    error_embed,
)


DUEL_STATUS_NAMES = {
    "open": "CHALLENGE",
    "running": "IN PROGRESS",
    "finished": "FINISHED",
    "cancelled": "CANCELLED",
}


def build_duel_embed(
    activity: Activity,
    challenger_id: int,
    opponent_id: int,
) -> discord.Embed:
    status = DUEL_STATUS_NAMES.get(
        activity.status,
        activity.status.upper(),
    )

    if activity.status == "open":
        description = (
            f"<@{challenger_id}> бросает вызов "
            f"<@{opponent_id}>.\n\n"
            f"Ответ за соперником."
        )

    elif activity.status == "running":
        description = (
            f"<@{challenger_id}> "
            f"⚔ "
            f"<@{opponent_id}>\n\n"
            f"Дуэль началась."
        )

    elif activity.status == "cancelled":
        description = (
            f"<@{challenger_id}> "
            f"× "
            f"<@{opponent_id}>\n\n"
            f"Вызов закрыт."
        )

    else:
        description = (
            f"<@{challenger_id}> "
            f"⚔ "
            f"<@{opponent_id}>"
        )

    embed = eden_embed(
        title="✦ DUEL",
        description=description,
    )

    embed.add_field(
        name="CHALLENGER",
        value=f"<@{challenger_id}>",
        inline=True,
    )

    embed.add_field(
        name="OPPONENT",
        value=f"<@{opponent_id}>",
        inline=True,
    )

    embed.add_field(
        name="STATUS",
        value=f"`{status}`",
        inline=True,
    )

    embed.set_footer(
        text=(
            f"DUEL #{activity.activity_id}"
        )
    )

    return embed


class DuelView(
    discord.ui.View
):
    def __init__(
        self,
        activity_id: int,
        challenger_id: int,
        opponent_id: int,
    ):
        super().__init__(
            timeout=None
        )

        self.activity_id = activity_id
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id

        self.action_lock = (
            asyncio.Lock()
        )

    async def get_duel(
        self,
        interaction: discord.Interaction,
    ) -> Activity | None:
        if interaction.guild is None:
            return None

        activity = await get_activity(
            guild_id=interaction.guild.id,
            activity_id=self.activity_id,
        )

        if (
            activity is None
            or activity.type != "duel"
        ):
            return None

        return activity

    @discord.ui.button(
        label="ACCEPT",
        style=discord.ButtonStyle.success,
        custom_id="duel_accept",
    )
    async def accept_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Принять вызов может только соперник.",
                ephemeral=True,
            )
            return

        async with self.action_lock:
            activity = await self.get_duel(
                interaction
            )

            if activity is None:
                await interaction.response.send_message(
                    embed=error_embed(
                        title="DUEL не найден",
                    ),
                    ephemeral=True,
                )
                return

            if activity.status != "open":
                await interaction.response.send_message(
                    "Этот вызов уже закрыт.",
                    ephemeral=True,
                )
                return

            result, activity = (
                await change_activity_status(
                    guild_id=interaction.guild.id,
                    activity_id=self.activity_id,
                    new_status="running",
                )
            )

            if (
                result != "changed"
                or activity is None
            ):
                await interaction.response.send_message(
                    "Не удалось принять вызов.",
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(
                content=None,
                embed=build_duel_embed(
                    activity=activity,
                    challenger_id=self.challenger_id,
                    opponent_id=self.opponent_id,
                ),
                view=None,
            )

            self.stop()

    @discord.ui.button(
        label="DECLINE",
        style=discord.ButtonStyle.danger,
        custom_id="duel_decline",
    )
    async def decline_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Отклонить вызов может только соперник.",
                ephemeral=True,
            )
            return

        async with self.action_lock:
            activity = await self.get_duel(
                interaction
            )

            if activity is None:
                await interaction.response.send_message(
                    "DUEL не найден.",
                    ephemeral=True,
                )
                return

            if activity.status != "open":
                await interaction.response.send_message(
                    "Этот вызов уже закрыт.",
                    ephemeral=True,
                )
                return

            result, activity = (
                await change_activity_status(
                    guild_id=interaction.guild.id,
                    activity_id=self.activity_id,
                    new_status="cancelled",
                )
            )

            if (
                result != "changed"
                or activity is None
            ):
                await interaction.response.send_message(
                    "Не удалось отклонить вызов.",
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(
                content=None,
                embed=build_duel_embed(
                    activity=activity,
                    challenger_id=self.challenger_id,
                    opponent_id=self.opponent_id,
                ),
                view=None,
            )

            self.stop()

    @discord.ui.button(
        label="CANCEL",
        style=discord.ButtonStyle.secondary,
        custom_id="duel_cancel",
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.user.id != self.challenger_id:
            await interaction.response.send_message(
                "Отозвать вызов может только его автор.",
                ephemeral=True,
            )
            return

        async with self.action_lock:
            activity = await self.get_duel(
                interaction
            )

            if activity is None:
                await interaction.response.send_message(
                    "DUEL не найден.",
                    ephemeral=True,
                )
                return

            if activity.status != "open":
                await interaction.response.send_message(
                    (
                        "Начавшуюся дуэль "
                        "уже нельзя отозвать."
                    ),
                    ephemeral=True,
                )
                return

            result, activity = (
                await change_activity_status(
                    guild_id=interaction.guild.id,
                    activity_id=self.activity_id,
                    new_status="cancelled",
                )
            )

            if (
                result != "changed"
                or activity is None
            ):
                await interaction.response.send_message(
                    "Не удалось отменить вызов.",
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(
                content=None,
                embed=build_duel_embed(
                    activity=activity,
                    challenger_id=self.challenger_id,
                    opponent_id=self.opponent_id,
                ),
                view=None,
            )

            self.stop()