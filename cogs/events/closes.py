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
from services.close_results import (
    confirm_close_result,
    dispute_close_result,
    init_close_results,
    propose_close_result,
)
from services.close_teams import (
    TEAM_MODE_CAPTAINS,
    TEAM_MODE_RANDOM,
    assign_random_teams,
    create_close_settings,
    get_close_settings,
    init_close_teams,
    pick_close_player,
    prepare_captain_draft,
    set_close_captains,
)
from views.activity.activity_view import (
    ActivityView,
    build_activity_embed,
)


CLOSE_SIZES = [
    app_commands.Choice(name="2×2 · 4 игрока", value=4),
    app_commands.Choice(name="3×3 · 6 игроков", value=6),
    app_commands.Choice(name="4×4 · 8 игроков", value=8),
    app_commands.Choice(name="5×5 · 10 игроков", value=10),
]


class Closes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        await init_close_teams()
        await init_close_results()

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
        description="Создать командный CLOSE",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.choices(
        team_mode=[
            app_commands.Choice(
                name="Случайные команды",
                value=TEAM_MODE_RANDOM,
            ),
            app_commands.Choice(
                name="Выбор капитанами",
                value=TEAM_MODE_CAPTAINS,
            ),
        ],
        team_size=CLOSE_SIZES,
    )
    async def create_close(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        team_mode: app_commands.Choice[str],
        team_size: app_commands.Choice[int],
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer()

        activity = None

        try:
            activity = await create_activity(
                guild_id=interaction.guild.id,
                activity_type="close",
                title=title,
                description=description,
                host_id=interaction.user.id,
                max_participants=team_size.value,
            )

            await create_close_settings(
                activity_id=activity.activity_id,
                team_mode=team_mode.value,
            )

        except ValueError as error:
            await interaction.followup.send(
                str(error),
                ephemeral=True,
            )
            return

        except Exception as error:
            if activity is not None:
                try:
                    await change_activity_status(
                        guild_id=interaction.guild.id,
                        activity_id=activity.activity_id,
                        new_status="cancelled",
                    )
                except Exception:
                    pass

            print(f"[CLOSE CREATE SETTINGS] {error}")

            await interaction.followup.send(
                "Не удалось создать CLOSE.",
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
                    await message.edit(view=None)
                except discord.HTTPException:
                    pass

            print(f"[CLOSE CREATE] {error}")

            await interaction.followup.send(
                "Не удалось опубликовать CLOSE. Он отменён.",
                ephemeral=True,
            )

    @app_commands.command(
        name="капитаны-клоза",
        description="Назначить капитанов CLOSE",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def close_captains(
        self,
        interaction: discord.Interaction,
        activity_id: int,
        captain_a: discord.Member,
        captain_b: discord.Member,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="close",
        )

        if activity is None:
            return

        result = await set_close_captains(
            activity_id=activity_id,
            captain_a_id=captain_a.id,
            captain_b_id=captain_b.id,
        )

        messages = {
            "same_captain": "Нужны два разных капитана.",
            "closed": "Капитанов можно назначить только до запуска CLOSE.",
            "wrong_mode": "У этого CLOSE выбран случайный режим команд.",
            "not_participant": "Оба капитана должны сначала нажать JOIN.",
            "not_found": "Настройки CLOSE не найдены.",
        }

        if result != "saved":
            await interaction.followup.send(
                messages.get(
                    result,
                    "Не удалось назначить капитанов.",
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            (
                f"Капитаны CLOSE **#{activity_id}** назначены:\n"
                f"Команда A: {captain_a.mention}\n"
                f"Команда B: {captain_b.mention}"
            ),
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

        await interaction.response.defer(ephemeral=True)

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

        required = activity.max_participants or 0

        if len(participants) != required:
            await interaction.followup.send(
                (
                    f"Для запуска этого CLOSE нужно ровно "
                    f"**{required}** участников.\n"
                    f"Сейчас записано: **{len(participants)}**."
                ),
                ephemeral=True,
            )
            return

        settings = await get_close_settings(activity_id)

        if settings is None:
            await interaction.followup.send(
                "Настройки этого CLOSE не найдены.",
                ephemeral=True,
            )
            return

        if settings.team_mode == TEAM_MODE_RANDOM:
            team_result = await assign_random_teams(
                activity_id
            )
        else:
            team_result = await prepare_captain_draft(
                activity_id
            )

            if team_result == "captains_missing":
                await interaction.followup.send(
                    (
                        "Сначала назначь двух капитанов командой "
                        "`/капитаны-клоза`."
                    ),
                    ephemeral=True,
                )
                return

        if team_result not in {"assigned", "ready"}:
            await interaction.followup.send(
                "Не удалось сформировать команды CLOSE.",
                ephemeral=True,
            )
            return

        status, activity = await change_activity_status(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            new_status="running",
        )

        if status != "changed" or activity is None:
            await interaction.followup.send(
                "Этот CLOSE уже нельзя запустить.",
                ephemeral=True,
            )
            return

        await self.refresh_close_message(activity)

        if settings.team_mode == TEAM_MODE_RANDOM:
            text = (
                f"CLOSE **#{activity_id}** запущен.\n"
                "Команды распределены случайно."
            )
        else:
            updated_settings = await get_close_settings(
                activity_id
            )

            if (
                updated_settings is None
                or updated_settings.draft_turn == "done"
            ):
                text = (
                    f"CLOSE **#{activity_id}** запущен.\n"
                    "Команды уже сформированы."
                )
            else:
                first_captain_id = (
                    updated_settings.captain_a_id
                    if updated_settings.draft_turn == "a"
                    else updated_settings.captain_b_id
                )

                text = (
                    f"CLOSE **#{activity_id}** запущен.\n"
                    f"Первым выбирает <@{first_captain_id}>."
                )

        await interaction.followup.send(
            text,
            ephemeral=True,
        )

    @app_commands.command(
        name="выбрать-игрока",
        description="Выбрать игрока в свою команду CLOSE",
    )
    @app_commands.guild_only()
    async def pick_player(
        self,
        interaction: discord.Interaction,
        activity_id: int,
        player: discord.Member,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="close",
        )

        if activity is None:
            return

        result = await pick_close_player(
            activity_id=activity_id,
            captain_id=interaction.user.id,
            player_id=player.id,
        )

        messages = {
            "wrong_turn": "Сейчас выбирает другой капитан.",
            "not_running": "Этот CLOSE сейчас не идёт.",
            "not_participant": "Этот пользователь не участвует в CLOSE.",
            "already_picked": "Этот игрок уже находится в команде.",
            "not_found": "Капитанский CLOSE не найден.",
        }

        if result not in {"picked", "finished"}:
            await interaction.followup.send(
                messages.get(
                    result,
                    "Не удалось выбрать игрока.",
                ),
                ephemeral=True,
            )
            return

        updated = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="close",
        )

        if updated is not None:
            await self.refresh_close_message(updated)

        if result == "finished":
            text = (
                f"{player.mention} выбран.\n"
                "Команды полностью сформированы."
            )
        else:
            updated_settings = await get_close_settings(
                activity_id
            )

            if updated_settings is None:
                text = f"{player.mention} добавлен в команду."
            else:
                next_captain_id = (
                    updated_settings.captain_a_id
                    if updated_settings.draft_turn == "a"
                    else updated_settings.captain_b_id
                )

                text = (
                    f"{player.mention} добавлен в команду.\n"
                    f"Теперь выбирает <@{next_captain_id}>."
                )

        await interaction.followup.send(
            text,
            ephemeral=True,
        )

    @app_commands.command(
        name="результат-клоза",
        description="Указать победившую команду CLOSE",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    @app_commands.choices(
        winner_team=[
            app_commands.Choice(
                name="Команда A",
                value="a",
            ),
            app_commands.Choice(
                name="Команда B",
                value="b",
            ),
        ]
    )
    async def close_result(
        self,
        interaction: discord.Interaction,
        activity_id: int,
        winner_team: app_commands.Choice[str],
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="close",
        )

        if activity is None:
            return

        result = await propose_close_result(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            winner_team=winner_team.value,
            submitted_by=interaction.user.id,
        )

        messages = {
            "not_running": "Этот CLOSE сейчас не идёт.",
            "teams_incomplete": "Сначала полностью сформируй команды.",
            "already_pending": "Результат этого CLOSE уже ожидает подтверждения.",
            "not_found": "CLOSE не найден.",
        }

        if result != "created":
            await interaction.followup.send(
                messages.get(
                    result,
                    "Не удалось сохранить результат CLOSE.",
                ),
                ephemeral=True,
            )
            return

        losing_team = "B" if winner_team.value == "a" else "A"

        await interaction.followup.send(
            (
                f"Победителем CLOSE **#{activity_id}** указана "
                f"**команда {winner_team.name[-1]}**.\n"
                f"Результат должен подтвердить представитель "
                f"команды {losing_team}."
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="подтвердить-клоз",
        description="Подтвердить результат CLOSE",
    )
    @app_commands.guild_only()
    async def confirm_close(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        status, activity = await confirm_close_result(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            confirmed_by=interaction.user.id,
        )

        messages = {
            "not_allowed": (
                "Подтвердить результат должен представитель "
                "проигравшей команды."
            ),
            "not_found": "Ожидающий подтверждения результат не найден.",
            "not_pending": "Этот результат уже не ожидает подтверждения.",
            "not_running": "Этот CLOSE уже не идёт.",
        }

        if status != "confirmed" or activity is None:
            await interaction.followup.send(
                messages.get(
                    status,
                    "Не удалось подтвердить результат CLOSE.",
                ),
                ephemeral=True,
            )
            return

        await self.refresh_close_message(activity)

        await interaction.followup.send(
            (
                f"Результат CLOSE **#{activity_id}** подтверждён.\n"
                "Матч записан в общий прогресс."
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="оспорить-клоз",
        description="Оспорить предложенный результат CLOSE",
    )
    @app_commands.guild_only()
    async def dispute_close(
        self,
        interaction: discord.Interaction,
        activity_id: int,
    ):
        if interaction.guild is None:
            return

        await interaction.response.defer(ephemeral=True)

        result = await dispute_close_result(
            guild_id=interaction.guild.id,
            activity_id=activity_id,
            disputed_by=interaction.user.id,
        )

        messages = {
            "not_allowed": (
                "Оспорить результат должен представитель "
                "проигравшей команды."
            ),
            "not_found": "Ожидающий подтверждения результат не найден.",
            "not_pending": "Этот результат уже не ожидает подтверждения.",
        }

        if result != "disputed":
            await interaction.followup.send(
                messages.get(
                    result,
                    "Не удалось оспорить результат CLOSE.",
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            (
                f"Результат CLOSE **#{activity_id}** отклонён.\n"
                "Администратор может указать результат заново."
            ),
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

        await interaction.response.defer(ephemeral=True)

        activity = await get_activity_for_command(
            interaction=interaction,
            activity_id=activity_id,
            activity_type="close",
        )

        if activity is None:
            return

        if activity.status not in {"open", "running"}:
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

        if status != "changed" or activity is None:
            await interaction.followup.send(
                "Не удалось отменить CLOSE.",
                ephemeral=True,
            )
            return

        await self.refresh_close_message(activity)

        await interaction.followup.send(
            f"CLOSE **#{activity_id}** отменён.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Closes(bot))
