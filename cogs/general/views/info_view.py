import discord

from discord import app_commands
from discord.ext import commands

from config.theme import EDEN_GOLD, EDEN_GREEN, EDEN_ASH

class ServerInfoView(discord.ui.View):
    def __init__(self, guild: discord.Guild, user_id: int):
        super().__init__(timeout=120)

        self.guild = guild
        self.user_id = user_id


    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Эта страница открыта другим путником.",
                ephemeral=True
            )
            return False

        return True