import discord
import random
from utils.embeds import (
    eden_embed,
    success_embed,
    error_embed,
)

class CoinView(discord.ui.View):
    def __init__(self, player_id: int):
        super().__init__(timeout=60)
        self.player_id = player_id

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.player_id:
            embed = error_embed(
                title="Чужая монета",
                description="Этот бросок принадлежит другому путнику.",
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return False

        return True
    
    async def play(
            self,
            interaction: discord.Interaction,
            choice: str
    ):
        result = random.choice(["Орёл", "Решка"])
        if choice == result:
            embed = success_embed(
                title="🪙 Монета благосклонна",
                description=(
                    f"Выпало: **{result}**\n"
                    f"Ты выбрал: **{choice}**\n\n"
                    "**Победа.**"
                ),
            )
        else:
            embed = eden_embed(
                title="🪙 Монета решила иначе",
                description=(
                    f"Выпало: **{result}**\n"
                    f"Ты выбрал: **{choice}**\n\n"
                    "*В этот раз сад выбрал не тебя.*"
                ),
            )
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=self,
        )

    @discord.ui.button(
        label="Орёл",
        style=discord.ButtonStyle.primary
    )
    async def heads(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.play(interaction, "Орёл")

    @discord.ui.button(
        label="Решка",
        style=discord.ButtonStyle.secondary
    )
    async def tails(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.play(interaction, "Решка")
        
        