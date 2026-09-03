import asyncio

import discord

from services.activities import (
    Activity,
    ActivityParticipant,
    get_activity,
    get_activity_participants,
    join_activity,
    leave_activity,
)

from utils.embeds import (
    eden_embed,
    error_embed,
)


ACTIVITY_NAMES = {
    "event": "EVENT",
    "duel": "DUEL",
    "close": "CLOSE",
    "tribune": "TRIBUNE",
}


STATUS_NAMES = {
    "open": "OPEN",
    "running": "IN PROGRESS",
    "finished": "FINISHED",
    "cancelled": "CANCELLED",
}


def build_activity_embed(
    activity: Activity,
    participants: list[ActivityParticipant],
) -> discord.Embed:
    activity_name = ACTIVITY_NAMES.get(
        activity.type,
        activity.type.upper(),
    )

    status_name = STATUS_NAMES.get(
        activity.status,
        activity.status.upper(),
    )

    embed = eden_embed(
        title=(
            f"✦ {activity_name} · "
            f"{activity.title}"
        ),
        description=(
            activity.description
            or "Описание не указано."
        ),
    )

    embed.add_field(
        name="Организатор",
        value=f"<@{activity.host_id}>",
        inline=True,
    )

    if activity.max_participants is None:
        count_text = str(
            len(participants)
        )
    else:
        count_text = (
            f"{len(participants)} / "
            f"{activity.max_participants}"
        )

    embed.add_field(
        name="Участники",
        value=f"`{count_text}`",
        inline=True,
    )

    embed.add_field(
        name="Статус",
        value=f"`{status_name}`",
        inline=True,
    )

    if participants:
        shown = participants[:15]

        participant_text = "\n".join(
            f"<@{participant.user_id}>"
            for participant in shown
        )

        if len(participants) > 15:
            participant_text += (
                f"\nи ещё "
                f"{len(participants) - 15}..."
            )
    else:
        participant_text = (
            "Сад пока пуст."
        )

    embed.add_field(
        name="Участники сада",
        value=participant_text,
        inline=False,
    )

    embed.set_footer(
        text=(
            f"ACTIVITY #{activity.activity_id}"
        )
    )

    return embed


class ActivityView(
    discord.ui.View
):
    def __init__(
        self,
        activity_id: int,
    ):
        super().__init__(
            timeout=None
        )

        self.activity_id = activity_id

        # Не даём двум кликам одновременно
        # перезаписать карточку.
        self.action_lock = (
            asyncio.Lock()
        )

    def disable_buttons(
        self,
    ) -> None:
        self.join_button.disabled = True
        self.leave_button.disabled = True

    async def get_state(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.guild is None:
            return None, []

        activity = await get_activity(
            guild_id=interaction.guild.id,
            activity_id=self.activity_id,
        )

        if activity is None:
            return None, []

        participants = (
            await get_activity_participants(
                activity_id=self.activity_id
            )
        )

        return (
            activity,
            participants,
        )

    @discord.ui.button(
        label="JOIN",
        style=discord.ButtonStyle.secondary,
        custom_id="activity_join",
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            return

        async with self.action_lock:
            result = await join_activity(
                guild_id=interaction.guild.id,
                activity_id=self.activity_id,
                user_id=interaction.user.id,
            )

            if result == "already_joined":
                await interaction.response.send_message(
                    "Ты уже участвуешь.",
                    ephemeral=True,
                )
                return

            if result == "full":
                await interaction.response.send_message(
                    "Свободных мест больше нет.",
                    ephemeral=True,
                )
                return

            if result in {
                "closed",
                "not_found",
            }:
                await interaction.response.send_message(
                    embed=error_embed(
                        title="Активность недоступна",
                        description=(
                            "К этой активности "
                            "уже нельзя присоединиться."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            activity, participants = (
                await self.get_state(
                    interaction
                )
            )

            if activity is None:
                await interaction.response.send_message(
                    embed=error_embed(
                        title="Активность не найдена",
                        description=(
                            "Не удалось обновить "
                            "карточку активности."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(
                embed=build_activity_embed(
                    activity,
                    participants,
                ),
                view=self,
            )

    @discord.ui.button(
        label="LEAVE",
        style=discord.ButtonStyle.secondary,
        custom_id="activity_leave",
    )
    async def leave_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            return

        async with self.action_lock:
            result = await leave_activity(
                guild_id=interaction.guild.id,
                activity_id=self.activity_id,
                user_id=interaction.user.id,
            )

            if result == "not_joined":
                await interaction.response.send_message(
                    "Тебя нет среди участников.",
                    ephemeral=True,
                )
                return

            if result in {
                "closed",
                "not_found",
            }:
                await interaction.response.send_message(
                    embed=error_embed(
                        title="Активность недоступна",
                        description=(
                            "Список участников "
                            "уже закрыт."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            activity, participants = (
                await self.get_state(
                    interaction
                )
            )

            if activity is None:
                await interaction.response.send_message(
                    embed=error_embed(
                        title="Активность не найдена",
                        description=(
                            "Не удалось обновить "
                            "карточку активности."
                        ),
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.edit_message(
                embed=build_activity_embed(
                    activity,
                    participants,
                ),
                view=self,
            )