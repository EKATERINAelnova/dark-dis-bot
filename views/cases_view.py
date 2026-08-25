import discord

from config.economy import (
    CURRENCY_SYMBOL,
)

from services.cases import (
    CaseOpenResult,
    open_eden_case,
)

from utils.embeds import (
    eden_embed,
    error_embed,
)


class CasesView(discord.ui.View):
    def __init__(
        self,
        player_id: int,
        guild_id: int,
    ):
        super().__init__(
            timeout=180
        )

        self.player_id = player_id
        self.guild_id = guild_id

        self.processing = False

    # =====================================================
    # OWNER CHECK
    # =====================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if (
            interaction.user.id
            != self.player_id
        ):
            await interaction.response.send_message(
                embed=error_embed(
                    title="Чужое хранилище",
                    description=(
                        "Этот EDEN CASE "
                        "принадлежит другой душе."
                    ),
                ),
                ephemeral=True,
            )

            return False

        return True

    # =====================================================
    # RESULT
    # =====================================================

    def build_result_embed(
        self,
        result: CaseOpenResult,
    ) -> discord.Embed:
        reward = result.reward

        if reward.kind == "currency":
            reward_text = (
                f"Ты получил "
                f"**{reward.amount} "
                f"{CURRENCY_SYMBOL}**."
            )

        else:
            reward_text = (
                f"Ты получил "
                f"**{reward.amount} XP**."
            )

        embed = eden_embed(
            title="✦ EDEN CASE",
            description=(
                f"`{reward.rarity}`\n\n"
                f"{reward_text}"
            ),
        )

        embed.add_field(
            name="Награда",
            value=reward.title,
            inline=True,
        )

        embed.add_field(
            name="Осталось",
            value=f"`{result.cases_left}`",
            inline=True,
        )

        if result.bonus_cases > 0:
            embed.add_field(
                name="Новый уровень",
                value=(
                    f"`{result.new_level}`\n"
                    f"+{result.bonus_cases} EDEN CASE"
                ),
                inline=False,
            )

        return embed

    # =====================================================
    # OPEN
    # =====================================================
    @discord.ui.button(
        label="OPEN",
        style=discord.ButtonStyle.secondary,
    )
    async def open_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.processing:
            return

        self.processing = True

        try:
            result = await open_eden_case(
                guild_id=self.guild_id,
                user_id=self.player_id,
            )

            # =========================================
            # NO CASES
            # =========================================

            if result is None:
                button.disabled = True
                button.label = "EMPTY"

                await interaction.response.edit_message(
                    embed=eden_embed(
                        title="✦ EDEN CASES",
                        description=(
                            "Хранилище пусто.\n\n"
                            "Следующий кейс появится "
                            "после нового уровня."
                        ),
                    ),
                    view=self,
                )

                return

            # =========================================
            # BUTTON STATE
            # =========================================

            if result.cases_left <= 0:
                button.disabled = True
                button.label = "EMPTY"

            else:
                button.label = "OPEN AGAIN"

            # =========================================
            # RESULT
            # =========================================

            await interaction.response.edit_message(
                embed=self.build_result_embed(
                    result
                ),
                view=self,
            )

        finally:
            self.processing = False