import discord

from config.theme import (
    EDEN_GOLD,
    EDEN_GREEN,
    EDEN_ASH,
    EDEN_RED,
)


FOOTER_TEXT = "LOST EDEN · RIMAY"

CASINO_AUTHOR = ""
CASINO_FOOTER = (
    "LOST EDEN · RIMAY  •  "
    "Сад помнит каждую ставку"
)


# =========================================================
# BASE
# =========================================================

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


# =========================================================
# ОБЫЧНЫЕ EMBEDS
# =========================================================

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


# =========================================================
# CASINO BASE
# =========================================================

def casino_embed(
    title: str,
    description: str | None = None,
    *,
    colour: int = EDEN_GOLD,
) -> discord.Embed:
    """
    Базовый embed казино.

    Используется для игровых экранов:
    ставки, Blackjack, Roulette, Slots.
    """

    embed = discord.Embed(
        title=title,
        description=description,
        colour=colour,
    )

    embed.set_author(
        name=CASINO_AUTHOR
    )

    embed.set_footer(
        text=CASINO_FOOTER
    )

    return embed


# =========================================================
# CASINO STATES
# =========================================================

def casino_success_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return casino_embed(
        title=title,
        description=description,
        colour=EDEN_GREEN,
    )


def casino_warning_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return casino_embed(
        title=title,
        description=description,
        colour=EDEN_ASH,
    )


def casino_error_embed(
    title: str,
    description: str | None = None,
) -> discord.Embed:
    return casino_embed(
        title=title,
        description=description,
        colour=EDEN_RED,
    )