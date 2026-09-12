import discord
from discord import app_commands
from discord.ext import commands

from services.verification_roles import is_member_verified
from utils.embeds import eden_embed


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="старт",
        description="Посмотреть первые шаги в LOST EDEN",
    )
    @app_commands.guild_only()
    async def start(
        self,
        interaction: discord.Interaction,
    ):
        if not isinstance(interaction.user, discord.Member):
            return

        try:
            verified = is_member_verified(interaction.user)
            verification_configured = True
        except RuntimeError:
            verified = False
            verification_configured = False

        if not verification_configured:
            status = "Верификация пока не настроена администрацией."
        elif verified:
            status = "Верификация пройдена. Путь в Сад открыт."
        else:
            status = "Ожидается подтверждение верификации модератором."

        embed = eden_embed(
            title="✦ ПЕРВЫЕ ШАГИ",
            description=(
                f"{status}\n\n"
                "**1.** Ознакомься с правилами и устройством сервера.\n"
                "**2.** Дождись подтверждения верификации.\n"
                "**3.** Открой `/прогресс` и `/профиль`.\n"
                "**4.** Проверь `/достижения` и ежедневный `/ритуал`.\n"
                "**5.** Участвуй в EVENT, DUEL и CLOSE."
            ),
        )

        if verified:
            embed.add_field(
                name="Сейчас",
                value=(
                    "Можно начинать копить XP, открывать EDEN CASES "
                    "и собирать достижения."
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name="Сейчас",
                value=(
                    "Сначала дождись роли подтверждённого участника."
                ),
                inline=False,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Onboarding(bot))
