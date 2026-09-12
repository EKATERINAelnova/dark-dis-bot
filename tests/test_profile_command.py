import discord
import pytest

from discord.ext import commands

from cogs.general import general
from cogs.general import profile


@pytest.mark.asyncio
async def test_redesigned_profile_replaces_legacy_command():
    bot = commands.Bot(
        command_prefix="!",
        intents=discord.Intents.none(),
    )

    await general.setup(bot)
    legacy_command = bot.tree.get_command("профиль")

    assert legacy_command is not None

    await profile.setup(bot)
    current_command = bot.tree.get_command("профиль")

    assert current_command is not None
    assert current_command is not legacy_command
    assert bot.get_cog("Profile") is not None
