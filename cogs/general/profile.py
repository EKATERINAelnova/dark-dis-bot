import discord

from discord import app_commands
from discord.ext import commands

from services.member_progress import get_member_progress
from services.verification_roles import (
    get_verified_role_id,
    is_member_verified,
)
from utils.embeds import (
    eden_embed,
    error_embed,
)
from utils.profile_card_v2 import (
    ProfileCardData,
    create_profile_card_v2,
)


def get_verification_status(
    member: discord.Member,
) -> str:
    try:
        role_id = get_verified_role_id()
    except RuntimeError:
        return "unconfigured"

    if role_id is None:
        return "unconfigured"

    return (
        "verified"
        if is_member_verified(member)
        else "pending"
    )


class Profile(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="профиль",
        description="Открыть профиль участника сада",
    )
    @app_commands.guild_only()
    async def profile(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        if interaction.guild is None:
            return

        if user is None:
            if not isinstance(
                interaction.user,
                discord.Member,
            ):
                return

            user = interaction.user

        await interaction.response.defer()

        progress = await get_member_progress(
            guild_id=interaction.guild.id,
            user_id=user.id,
        )

        status = get_verification_status(user)

        milestone_name = (
            progress.current_milestone[1]
            if progress.current_milestone
            else None
        )

        card_data = ProfileCardData(
            level=progress.level,
            rank=progress.rank,
            currency=progress.stats.currency,
            messages=progress.stats.messages,
            voice_seconds=progress.stats.voice_seconds,
            total_xp=progress.stats.xp,
            xp_to_next_level=progress.xp_to_next_level,
            eden_cases=progress.stats.eden_cases,
            verification_status=status,
            milestone_name=milestone_name,
        )

        try:
            card = await create_profile_card_v2(
                user=user,
                data=card_data,
            )
        except (FileNotFoundError, RuntimeError) as error:
            await interaction.followup.send(
                embed=error_embed(
                    title="Профиль не собран",
                    description=str(error),
                ),
                ephemeral=True,
            )
            return

        file = discord.File(
            card,
            filename="profile.png",
        )

        activities = progress.activities

        embed = eden_embed(
            title=f"✦ ПРОФИЛЬ · {user.display_name}",
            description=(
                f"{user.mention}\n"
                "*След, который участник оставляет в Саду.*"
            ),
        )

        embed.set_image(
            url="attachment://profile.png"
        )

        embed.add_field(
            name="ДОСТИЖЕНИЯ",
            value=(
                f"Открыто: **{progress.achievements_unlocked}/"
                f"{progress.achievements_total}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="ИВЕНТЫ",
            value=(
                f"Участий: **{activities.events.participations}**"
            ),
            inline=True,
        )

        embed.add_field(
            name="ДУЭЛИ / КЛОЗЫ",
            value=(
                f"Дуэли: **{activities.duels.wins}/{activities.duels.participations}** "
                f"({activities.duels.winrate}%)\n"
                f"Клозы: **{activities.closes.wins}/{activities.closes.participations}** "
                f"({activities.closes.winrate}%)"
            ),
            inline=False,
        )

        embed.set_footer(
            text=(
                "LOST EDEN · RIMAY  •  "
                "подробная статистика: /прогресс"
            )
        )

        await interaction.followup.send(
            embed=embed,
            file=file,
        )


async def setup(
    bot: commands.Bot,
) -> None:
    existing = bot.tree.get_command(
        "профиль"
    )

    if existing is not None:
        bot.tree.remove_command(
            "профиль"
        )

    await bot.add_cog(
        Profile(bot)
    )
