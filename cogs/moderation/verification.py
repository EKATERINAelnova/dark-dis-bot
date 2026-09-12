import discord

from discord import app_commands
from discord.ext import commands

from services.verification_roles import (
    get_verified_role_id,
    is_member_verified,
    set_verified_role,
)
from utils.embeds import (
    eden_embed,
    error_embed,
    success_embed,
)


VERIFICATION_BUTTON_ID = "lost_eden:verification:pass"


class VerificationView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Пройти верификацию",
        style=discord.ButtonStyle.success,
        emoji="🌿",
        custom_id=VERIFICATION_BUTTON_ID,
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if (
            interaction.guild is None
            or not isinstance(
                interaction.user,
                discord.Member,
            )
        ):
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация недоступна",
                    description=(
                        "Пройти верификацию можно только внутри сервера."
                    ),
                ),
                ephemeral=True,
            )
            return

        role_id = get_verified_role_id()

        if role_id is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "Администратору нужно указать `VERIFIED_ROLE_ID`."
                    ),
                ),
                ephemeral=True,
            )
            return

        if interaction.guild.get_role(role_id) is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Роль не найдена",
                    description=(
                        "Роль верификации больше не существует на сервере."
                    ),
                ),
                ephemeral=True,
            )
            return

        if is_member_verified(interaction.user):
            await interaction.response.send_message(
                embed=success_embed(
                    title="Ты уже верифицирован",
                    description=(
                        "Доступ в основную часть LOST EDEN уже открыт."
                    ),
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        try:
            role = await set_verified_role(
                member=interaction.user,
                verified=True,
            )
        except RuntimeError as error:
            await interaction.followup.send(
                embed=error_embed(
                    title="Не удалось пройти верификацию",
                    description=str(error),
                ),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed(
                    title="Не удалось выдать роль",
                    description=(
                        "У бота недостаточно прав. Роль бота должна быть "
                        "выше роли верификации."
                    ),
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                embed=error_embed(
                    title="Ошибка Discord",
                    description=(
                        "Не удалось изменить роль. Попробуй нажать кнопку ещё раз."
                    ),
                ),
                ephemeral=True,
            )
            return

        if role is None:
            await interaction.followup.send(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "Не удалось определить роль верификации."
                    ),
                ),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            embed=success_embed(
                title="Верификация пройдена",
                description=(
                    f"Тебе выдана роль **{role.name}**.\n\n"
                    "Добро пожаловать в LOST EDEN."
                ),
            ),
            ephemeral=True,
        )


class VerificationAdmin(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

    @app_commands.command(
        name="панель-верификации",
        description="Опубликовать панель верификации с кнопкой",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    @app_commands.checks.bot_has_permissions(
        manage_roles=True
    )
    async def verification_panel(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if interaction.guild is None:
            return

        role_id = get_verified_role_id()

        if role_id is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "В `.env` не указан `VERIFIED_ROLE_ID`."
                    ),
                ),
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(
            role_id
        )

        if role is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Роль не найдена",
                    description=(
                        f"На сервере нет роли с ID `{role_id}`."
                    ),
                ),
                ephemeral=True,
            )
            return

        embed = eden_embed(
            title="✦ ВРАТА LOST EDEN",
            description=(
                "Чтобы войти в основную часть сервера, "
                "пройди верификацию.\n\n"
                "Нажимая кнопку ниже, ты подтверждаешь, что "
                "ознакомился с правилами сервера и принимаешь их.\n\n"
                "После верификации тебе автоматически откроются "
                "основные каналы Сада."
            ),
        )

        embed.set_footer(
            text="LOST EDEN · RIMAY  •  We don't return. We rebuild."
        )

        await interaction.response.send_message(
            embed=embed,
            view=VerificationView(),
        )

    @app_commands.command(
        name="верифицировать",
        description="Выдать участнику роль верификации",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    @app_commands.checks.bot_has_permissions(
        manage_roles=True
    )
    async def verify_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if interaction.guild is None:
            return

        if get_verified_role_id() is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "В `.env` не указан `VERIFIED_ROLE_ID`."
                    ),
                ),
                ephemeral=True,
            )
            return

        if is_member_verified(user):
            await interaction.response.send_message(
                embed=error_embed(
                    title="Уже верифицирован",
                    description=(
                        f"{user.mention} уже имеет роль верификации."
                    ),
                ),
                ephemeral=True,
            )
            return

        try:
            role = await set_verified_role(
                member=user,
                verified=True,
            )
        except RuntimeError as error:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Не удалось верифицировать",
                    description=str(error),
                ),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Не удалось выдать роль",
                    description=(
                        "Проверь, что роль бота находится выше роли "
                        "верификации и у бота есть право `Управлять ролями`."
                    ),
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Ошибка Discord",
                    description=(
                        "Discord не принял изменение роли. Попробуй ещё раз."
                    ),
                ),
                ephemeral=True,
            )
            return

        if role is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "Не удалось определить роль верификации."
                    ),
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                title="Участник верифицирован",
                description=(
                    f"{user.mention} получил роль **{role.name}**."
                ),
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="снять-верификацию",
        description="Снять с участника роль верификации",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    @app_commands.checks.bot_has_permissions(
        manage_roles=True
    )
    async def unverify_member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        if interaction.guild is None:
            return

        if get_verified_role_id() is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "В `.env` не указан `VERIFIED_ROLE_ID`."
                    ),
                ),
                ephemeral=True,
            )
            return

        if not is_member_verified(user):
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация отсутствует",
                    description=(
                        f"У {user.mention} нет роли верификации."
                    ),
                ),
                ephemeral=True,
            )
            return

        try:
            role = await set_verified_role(
                member=user,
                verified=False,
            )
        except RuntimeError as error:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Не удалось снять верификацию",
                    description=str(error),
                ),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Не удалось снять роль",
                    description=(
                        "Проверь, что роль бота находится выше роли "
                        "верификации и у бота есть право `Управлять ролями`."
                    ),
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Ошибка Discord",
                    description=(
                        "Discord не принял изменение роли. Попробуй ещё раз."
                    ),
                ),
                ephemeral=True,
            )
            return

        if role is None:
            await interaction.response.send_message(
                embed=error_embed(
                    title="Верификация не настроена",
                    description=(
                        "Не удалось определить роль верификации."
                    ),
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                title="Верификация снята",
                description=(
                    f"У {user.mention} снята роль **{role.name}**."
                ),
            ),
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    bot.add_view(
        VerificationView()
    )

    await bot.add_cog(
        VerificationAdmin(bot)
    )
