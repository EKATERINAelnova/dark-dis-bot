import discord

from discord import app_commands
from discord.ext import commands

from services.verification_roles import (
    get_verified_role_id,
    is_member_verified,
    set_verified_role,
)
from utils.embeds import (
    error_embed,
    success_embed,
)


class VerificationAdmin(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ) -> None:
        self.bot = bot

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
    await bot.add_cog(
        VerificationAdmin(bot)
    )
