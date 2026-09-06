import asyncio

import discord

from cogs.events.reward_helpers import (
    format_reward_bundle,
    process_xp_rewards,
)

from config.economy import (
    DUEL_WIN_REWARD,
)

from services.activities import (
    Activity,
    change_activity_status,
    get_activity,
)

from services.automatic_activity_rewards import (
    reward_duel_winner_automatically,
)

from services.duels import (
    DuelResult,
    confirm_duel_result,
    discard_duel_result,
    get_duel_result,
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
    result: DuelResult | None = None,
) -> discord.Embed:
    status = DUEL_STATUS_NAMES.get(
        activity.status,
        activity.status.upper(),
    )

    if (
        activity.status == "running"
        and result is not None
        and result.status == "pending"
    ):
        status = "RESULT PENDING"

    reward_text = format_reward_bundle(
        DUEL_WIN_REWARD
    )

    if activity.status == "open":
        description = (
            f"<@{challenger_id}> бросает вызов "
            f"<@{opponent_id}>.\n\n"
            f"Награда победителю: {reward_text}.\n"
            f"Ответ за соперником."
        )

    elif (
        activity.status == "running"
        and result is not None
        and result.status == "pending"
    ):
        description = (
            f"<@{challenger_id}> ⚔ "
            f"<@{opponent_id}>\n\n"
            f"Предложенный победитель: "
            f"<@{result.winner_id}>\n"
            f"Ожидается подтверждение результата."
        )

    elif activity.status == "running":
        description = (
            f"<@{challenger_id}> ⚔ "
            f"<@{opponent_id}>\n\n"
            f"Дуэль началась.\n"
            f"Награда победителю: {reward_text}."
        )

    elif activity.status == "finished":
        if (
            result is not None
            and result.status == "confirmed"
        ):
            description = (
                f"<@{challenger_id}> ⚔ "
                f"<@{opponent_id}>\n\n"
                f"Победитель: <@{result.winner_id}>\n"
                f"Награда: {reward_text}."
            )
        else:
            description = (
                f"<@{challenger_id}> ⚔ "
                f"<@{opponent_id}>\n\n"
                f"Дуэль завершена."
            )

    elif activity.status == "cancelled":
        description = (
            f"<@{challenger_id}> × "
            f"<@{opponent_id}>\n\n"
            f"Вызов закрыт."
        )

    else:
        description = (
            f"<@{challenger_id}> ⚔ "
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
        text=f"DUEL #{activity.activity_id}"
    )

    return embed


class DuelView(discord.ui.View):
    def __init__(
        self,
        activity_id: int,
        challenger_id: int,
        opponent_id: int,
    ):
        super().__init__(timeout=None)

        self.activity_id = activity_id
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.action_lock = asyncio.Lock()

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
                    "Начавшуюся дуэль уже нельзя отозвать.",
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


class DuelResultView(discord.ui.View):
    def __init__(
        self,
        activity_id: int,
        challenger_id: int,
        opponent_id: int,
        winner_id: int,
        submitted_by: int,
    ):
        super().__init__(timeout=None)

        self.activity_id = activity_id
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.winner_id = winner_id
        self.submitted_by = submitted_by
        self.action_lock = asyncio.Lock()

    async def check_resolver(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id == self.submitted_by:
            await interaction.response.send_message(
                "Подтвердить собственный отчёт нельзя.",
                ephemeral=True,
            )
            return False

        other_player = (
            self.opponent_id
            if self.submitted_by == self.challenger_id
            else self.challenger_id
        )

        permissions = getattr(
            interaction.user,
            "guild_permissions",
            None,
        )

        is_admin = bool(
            permissions
            and permissions.manage_guild
        )

        if (
            interaction.user.id != other_player
            and not is_admin
        ):
            await interaction.response.send_message(
                (
                    "Подтвердить результат может "
                    "второй участник или администратор."
                ),
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="CONFIRM",
        style=discord.ButtonStyle.success,
        custom_id="duel_result_confirm",
    )
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            return

        if not await self.check_resolver(
            interaction
        ):
            return

        async with self.action_lock:
            status, activity = (
                await confirm_duel_result(
                    guild_id=interaction.guild.id,
                    activity_id=self.activity_id,
                    confirmed_by=interaction.user.id,
                )
            )

            if (
                status != "confirmed"
                or activity is None
            ):
                await interaction.response.send_message(
                    "Этот результат уже нельзя подтвердить.",
                    ephemeral=True,
                )
                return

            result = await get_duel_result(
                self.activity_id
            )

            reward_error = None

            if result is not None:
                try:
                    reward_results = (
                        await reward_duel_winner_automatically(
                            guild_id=interaction.guild.id,
                            activity_id=self.activity_id,
                            winner_id=result.winner_id,
                            actor_id=interaction.user.id,
                        )
                    )

                    await process_xp_rewards(
                        guild=interaction.guild,
                        results=reward_results,
                    )

                except Exception as error:
                    reward_error = error
                    print(
                        f"[DUEL AUTO REWARD] {error}"
                    )

            await interaction.response.edit_message(
                content=None,
                embed=build_duel_embed(
                    activity=activity,
                    challenger_id=self.challenger_id,
                    opponent_id=self.opponent_id,
                    result=result,
                ),
                view=None,
            )

            if reward_error is not None:
                await interaction.followup.send(
                    (
                        "Результат подтверждён, но автоматическая "
                        "награда не выдалась. Проверь логи бота."
                    ),
                    ephemeral=True,
                )

            self.stop()

    @discord.ui.button(
        label="DISPUTE",
        style=discord.ButtonStyle.danger,
        custom_id="duel_result_dispute",
    )
    async def dispute_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            return

        if not await self.check_resolver(
            interaction
        ):
            return

        async with self.action_lock:
            status = await discard_duel_result(
                guild_id=interaction.guild.id,
                activity_id=self.activity_id,
            )

            if status != "discarded":
                await interaction.response.send_message(
                    "Этот результат уже изменился.",
                    ephemeral=True,
                )
                return

            activity = await get_activity(
                guild_id=interaction.guild.id,
                activity_id=self.activity_id,
            )

            if activity is None:
                await interaction.response.send_message(
                    "DUEL не найден.",
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
