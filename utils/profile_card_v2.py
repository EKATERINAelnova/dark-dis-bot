from dataclasses import dataclass
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageFont

from utils.profile_card import (
    AVATAR_X,
    AVATAR_Y,
    FONT_PATH,
    PROFILE_TEMPLATE,
    draw_activity_stats,
    draw_balance_badge,
    draw_exp_stats,
    draw_level_block,
    draw_name_block,
    prepare_avatar,
    shorten_text,
)


BADGES_X = 435
BADGES_Y = 145
BADGE_HEIGHT = 28
BADGE_PADDING_X = 12
BADGE_GAP = 8
BADGE_RADIUS = 10
BADGE_FONT_SIZE = 12
BADGE_MAX_TEXT_WIDTH = 130
BADGE_RIGHT_LIMIT = 940

BADGE_TEXT_COLOR = "#EEDAC0"
BADGE_BG_COLOR = "#3D352F"
BADGE_VERIFIED_COLOR = "#4A7C59"
BADGE_PENDING_COLOR = "#604840"
BADGE_OUTLINE_COLOR = "#6A584B"


@dataclass(frozen=True)
class ProfileCardData:
    level: int
    rank: int
    currency: int
    messages: int
    voice_seconds: int
    total_xp: int
    xp_to_next_level: int
    eden_cases: int
    verification_status: str
    milestone_name: str | None = None


def get_profile_badges(
    data: ProfileCardData,
) -> list[tuple[str, str]]:
    if data.verification_status == "verified":
        verification_badge = (
            "VERIFIED",
            BADGE_VERIFIED_COLOR,
        )
    elif data.verification_status == "unconfigured":
        verification_badge = (
            "VERIFICATION OFF",
            BADGE_PENDING_COLOR,
        )
    else:
        verification_badge = (
            "PENDING",
            BADGE_PENDING_COLOR,
        )

    badges = [verification_badge]

    if data.milestone_name:
        badges.append(
            (
                data.milestone_name,
                BADGE_BG_COLOR,
            )
        )

    badges.append(
        (
            f"CASES · {data.eden_cases}",
            BADGE_BG_COLOR,
        )
    )

    return badges


def draw_profile_badges(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw = ImageDraw.Draw(card)
    font = ImageFont.truetype(
        FONT_PATH,
        BADGE_FONT_SIZE,
    )

    current_x = BADGES_X

    for text, background in get_profile_badges(data):
        text = shorten_text(
            draw=draw,
            text=text,
            font=font,
            max_width=BADGE_MAX_TEXT_WIDTH,
        )

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )
        text_width = bbox[2] - bbox[0]
        badge_width = text_width + BADGE_PADDING_X * 2

        if current_x + badge_width > BADGE_RIGHT_LIMIT:
            break

        draw.rounded_rectangle(
            (
                current_x,
                BADGES_Y,
                current_x + badge_width,
                BADGES_Y + BADGE_HEIGHT,
            ),
            radius=BADGE_RADIUS,
            fill=background,
            outline=BADGE_OUTLINE_COLOR,
            width=1,
        )

        draw.text(
            (
                current_x + badge_width / 2,
                BADGES_Y + BADGE_HEIGHT / 2,
            ),
            text,
            font=font,
            fill=BADGE_TEXT_COLOR,
            anchor="mm",
        )

        current_x += badge_width + BADGE_GAP


async def create_profile_card_v2(
    user: discord.Member,
    data: ProfileCardData,
) -> BytesIO:
    card = Image.open(
        PROFILE_TEMPLATE
    ).convert("RGBA")

    avatar = await prepare_avatar(user)
    card.paste(
        avatar,
        (AVATAR_X, AVATAR_Y),
        avatar,
    )

    draw_name_block(card, user)
    draw_profile_badges(card, data)
    draw_balance_badge(card, data)
    draw_level_block(card, data)
    draw_exp_stats(card, data)
    draw_activity_stats(card, data)

    buffer = BytesIO()
    card.save(
        buffer,
        format="PNG",
    )
    buffer.seek(0)

    return buffer
