import discord
import random

class CoinView(discord.ui.View):
    def __init__(self, player_id: int):
        super().__init__(timeout=60)
        self.player_id = player_id

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message(
                "Это не твоя игра.",
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
            text = f"Выпал {result}. Ты выиграл!"
        else:
            text = f"Выпал {result}. Ты проиграл."
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(
            content=text,
            view=self
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
        
        