import discord

from config.theme import (
    EDEN_GOLD,
    EDEN_GREEN,
    EDEN_ASH,
    EDEN_RED,
    EDEN_DARK,
)

FOOTER_TEXT = "LOST EDEN · RIMAY"

def casino_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return eden_embed(
        title=title,
        description=description,
        colour=EDEN_GOLD,
    )

def eden_embed(
    title: str | None = None,
    description: str | None = None,
    *,
    colour: int = EDEN_GOLD,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        colour=colour,
    )

    embed.set_footer(
        text=FOOTER_TEXT
    )

    return embed

def success_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return eden_embed(
        title=title,
        description=description,
        colour=EDEN_GREEN,
    )


def error_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return eden_embed(
        title=title,
        description=description,
        colour=EDEN_RED,
    )


def warning_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return eden_embed(
        title=title,
        description=description,
        colour=EDEN_ASH,
    )