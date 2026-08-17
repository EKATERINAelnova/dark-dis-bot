from io import BytesIO
from pathlib import Path
from dataclasses import dataclass

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps


BASE_DIR = Path(__file__).resolve().parents[1]

PROFILE_TEMPLATE = BASE_DIR / "assets" / "template.png"
FONT_PATH = BASE_DIR / "assets" / "Merriweather_24pt-Regular.ttf"
FONT_PATH2 = BASE_DIR / "assets" / "Marcellus-Regular.ttf"

# =========================
# AVATAR
# =========================
AVATAR_X = 72
AVATAR_Y = 95
AVATAR_SIZE = 195


# =========================
# NAME
# =========================
NAME_X = 435
NAME_Y = 50
NAME_MAX_WIDTH = 320
NAME_FONT_SIZE = 24
NAME_MIN_FONT_SIZE = 14
NAME_COLOR = "#C9A87C"

SECOND_NAME_MAX_WIDTH = 320
SECOND_NAME_FONT_SIZE = 14
SECOND_NAME_MIN_FONT_SIZE = 10
SECOND_NAME_COLOR = "#7A6B65"

NAME_LINE_GAP = 4


# =========================
# ROLES
# =========================
ROLES_X = 435
ROLES_Y = 145

ROLE_FONT_SIZE = 12
ROLE_TEXT_COLOR = "#EEDAC0"
ROLE_BG_COLOR = "#4A7C59"
ROLE_OUTLINE_COLOR = "#6A584B"

ROLE_HEIGHT = 28
ROLE_PADDING_X = 12
ROLE_GAP = 8
ROLE_RADIUS = 10

ROLE_MAX_COUNT = 4
ROLE_MAX_TEXT_WIDTH = 100


# =========================
# LEVEL / RANK / XP / ACTIVITY
# =========================
LEVEL_X = 540
LEVEL_Y = 257

NEXT_LEVEL_X = 825
NEXT_LEVEL_Y = 230

NEXT_LEVEL_FONT_SIZE = 24
NEXT_LEVEL_LABEL_FONT_SIZE = 12

RANK_X = 620
RANK_Y = 258

EXP_X = 827
EXP_Y = 277

XP_TO_NEXT_X = 827
XP_TO_NEXT_Y = 307

VOICE_X = 575
VOICE_Y = 373

MESSAGES_X = 865
MESSAGES_Y = 373


# =========================
# BALANCE BADGE
# =========================
BALANCE_RIGHT_X = 940
BALANCE_TOP_Y = 34

BALANCE_LABEL_FONT_SIZE = 10
BALANCE_VALUE_FONT_SIZE = 18

BALANCE_PADDING_X = 16
BALANCE_PADDING_Y = 10
BALANCE_GAP_Y = 6
BALANCE_RADIUS = 14

BALANCE_BG_COLOR = "#2B2421FF"
BALANCE_OUTLINE_COLOR = "#6A584B"
BALANCE_LABEL_COLOR = "#C9A87C"
BALANCE_VALUE_COLOR = "#EEDAC0"


# =========================
# GENERAL TEXT STYLES
# =========================
STATS_LABEL_COLOR = "#C9A87C"
STATS_VALUE_COLOR = "#C9A87C"

LEVEL_FONT_SIZE = 42
STAT_VALUE_FONT_SIZE = 14
STAT_LABEL_FONT_SIZE = 11


@dataclass
class ProfileStats:
    level: int
    rank: int
    currency: int
    messages: int
    voice_seconds: int
    total_xp: int
    xp_to_next_level: int


# =========================
# HELPERS
# =========================
def format_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_voice_time(voice_seconds: int) -> str:
    total_minutes = voice_seconds // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours} h {minutes:02} min"


def fit_text_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    start_size: int,
    max_width: int,
    min_size: int = 12
) -> ImageFont.FreeTypeFont:
    font_size = start_size

    while font_size >= min_size:
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return font

        font_size -= 1

    return ImageFont.truetype(font_path, min_size)


def shorten_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int
) -> str:
    bbox = draw.textbbox((0, 0), text, font=font)

    if bbox[2] - bbox[0] <= max_width:
        return text

    shortened = text

    while shortened:
        shortened = shortened[:-1]
        candidate = shortened + "..."

        bbox = draw.textbbox((0, 0), candidate, font=font)

        if bbox[2] - bbox[0] <= max_width:
            return candidate

    return "..."


def build_second_line(user: discord.Member) -> str:
    if user.discriminator != "0":
        return f"{user.name} #{user.discriminator}"
    return f"@{user.name}"


# =========================
# AVATAR
# =========================
async def prepare_avatar(user: discord.Member) -> Image.Image:
    avatar_bytes = await user.display_avatar.read()

    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    avatar = ImageOps.fit(
        avatar,
        (AVATAR_SIZE, AVATAR_SIZE),
        method=Image.Resampling.LANCZOS
    )

    mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1), fill=255)

    rounded_avatar = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    rounded_avatar.paste(avatar, (0, 0), mask)

    return rounded_avatar


# =========================
# DRAW NAME
# =========================
def draw_name_block(card: Image.Image, user: discord.Member) -> None:
    draw = ImageDraw.Draw(card)

    display_name = user.display_name
    second_line = build_second_line(user)

    name_font = fit_text_font(
        draw=draw,
        text=display_name,
        font_path=FONT_PATH,
        start_size=NAME_FONT_SIZE,
        max_width=NAME_MAX_WIDTH,
        min_size=NAME_MIN_FONT_SIZE
    )

    draw.text(
        (NAME_X, NAME_Y),
        display_name,
        font=name_font,
        fill=NAME_COLOR
    )

    name_bbox = draw.textbbox(
        (NAME_X, NAME_Y),
        display_name,
        font=name_font
    )
    second_line_y = name_bbox[3] + NAME_LINE_GAP

    second_font = fit_text_font(
        draw=draw,
        text=second_line,
        font_path=FONT_PATH2,
        start_size=SECOND_NAME_FONT_SIZE,
        max_width=SECOND_NAME_MAX_WIDTH,
        min_size=SECOND_NAME_MIN_FONT_SIZE
    )

    draw.text(
        (NAME_X, second_line_y),
        second_line,
        font=second_font,
        fill=SECOND_NAME_COLOR
    )


# =========================
# DRAW ROLES
# =========================
def draw_roles(card: Image.Image, user: discord.Member) -> None:
    draw = ImageDraw.Draw(card)

    font = ImageFont.truetype(FONT_PATH, ROLE_FONT_SIZE)

    roles = [
        role
        for role in reversed(user.roles)
        if role.name != "@everyone"
    ][:ROLE_MAX_COUNT]

    if not roles:
        return

    current_x = ROLES_X

    for role in roles:
        role_name = shorten_text(
            draw=draw,
            text=role.name,
            font=font,
            max_width=ROLE_MAX_TEXT_WIDTH
        )

        bbox = draw.textbbox((0, 0), role_name, font=font)
        text_width = bbox[2] - bbox[0]

        role_width = text_width + ROLE_PADDING_X * 2

        draw.rounded_rectangle(
            (
                current_x,
                ROLES_Y,
                current_x + role_width,
                ROLES_Y + ROLE_HEIGHT
            ),
            radius=ROLE_RADIUS,
            fill=ROLE_BG_COLOR,
            outline=ROLE_OUTLINE_COLOR,
            width=1
        )

        draw.text(
            (
                current_x + role_width / 2,
                ROLES_Y + ROLE_HEIGHT / 2
            ),
            role_name,
            font=font,
            fill=ROLE_TEXT_COLOR,
            anchor="mm"
        )

        current_x += role_width + ROLE_GAP


# =========================
# DRAW BALANCE BADGE
# =========================
def draw_balance_badge(card: Image.Image, stats: ProfileStats) -> None:
    draw = ImageDraw.Draw(card)

    label_font = ImageFont.truetype(FONT_PATH2, BALANCE_LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(FONT_PATH, BALANCE_VALUE_FONT_SIZE)

    label_text = "BALANCE"
    value_text = f"{format_number(stats.currency)}"

    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
    value_bbox = draw.textbbox((0, 0), value_text, font=value_font)

    label_width = label_bbox[2] - label_bbox[0]
    label_height = label_bbox[3] - label_bbox[1]

    value_width = value_bbox[2] - value_bbox[0]
    value_height = value_bbox[3] - value_bbox[1]

    content_width = max(label_width, value_width)
    badge_width = content_width + BALANCE_PADDING_X * 2
    badge_height = (
        label_height
        + BALANCE_GAP_Y
        + value_height
        + BALANCE_PADDING_Y * 2
    )

    x1 = BALANCE_RIGHT_X - badge_width
    y1 = BALANCE_TOP_Y
    x2 = BALANCE_RIGHT_X
    y2 = BALANCE_TOP_Y + badge_height

    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=BALANCE_RADIUS,
        outline=BALANCE_OUTLINE_COLOR,
        width=1
    )

    center_x = (x1 + x2) / 2

    label_y = y1 + BALANCE_PADDING_Y
    value_y = label_y + label_height + BALANCE_GAP_Y

    draw.text(
        (center_x, label_y),
        label_text,
        font=label_font,
        fill=BALANCE_LABEL_COLOR,
        anchor="ma"
    )

    draw.text(
        (center_x, value_y),
        value_text,
        font=value_font,
        fill=BALANCE_VALUE_COLOR,
        anchor="ma"
    )


# =========================
# DRAW LEVEL / RANK
# =========================
def draw_level_block(card: Image.Image, stats: ProfileStats) -> None:
    draw = ImageDraw.Draw(card)

    label_font = ImageFont.truetype(FONT_PATH2, STAT_LABEL_FONT_SIZE)
    level_font = ImageFont.truetype(FONT_PATH, LEVEL_FONT_SIZE)
    value_font = ImageFont.truetype(FONT_PATH, STAT_VALUE_FONT_SIZE)

    draw.text(
        (LEVEL_X, LEVEL_Y),
        str(stats.level),
        font=level_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )

    draw.text(
        (RANK_X, RANK_Y - 25),
        "RANK",
        font=label_font,
        fill=STATS_LABEL_COLOR,
        anchor="mm"
    )

    draw.text(
        (RANK_X, RANK_Y),
        f"#{stats.rank}",
        font=value_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )


# =========================
# DRAW XP
# =========================
def draw_exp_stats(
    card: Image.Image,
    stats: ProfileStats
) -> None:
    draw = ImageDraw.Draw(card)

    label_font = ImageFont.truetype(
        FONT_PATH2,
        10
    )

    value_font = ImageFont.truetype(
        FONT_PATH,
        STAT_VALUE_FONT_SIZE
    )

    next_level_font = ImageFont.truetype(
        FONT_PATH,
        NEXT_LEVEL_FONT_SIZE
    )

    next_level = stats.level + 1
    total_xp_text = format_number(stats.total_xp)
    xp_to_next_text = format_number(stats.xp_to_next_level)

    draw.text(
        (NEXT_LEVEL_X, NEXT_LEVEL_Y - 18),
        "NEXT LEVEL",
        font=label_font,
        fill=STATS_LABEL_COLOR,
        anchor="mm"
    )

    draw.text(
        (NEXT_LEVEL_X, NEXT_LEVEL_Y),
        str(next_level),
        font=next_level_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )

    draw.text(
        (EXP_X, EXP_Y),
        total_xp_text,
        font=value_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )

    draw.text(
        (XP_TO_NEXT_X, XP_TO_NEXT_Y),
        xp_to_next_text,
        font=value_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )


# =========================
# DRAW ACTIVITY
# =========================
def draw_activity_stats(card: Image.Image, stats: ProfileStats) -> None:
    draw = ImageDraw.Draw(card)

    value_font = ImageFont.truetype(FONT_PATH, STAT_VALUE_FONT_SIZE)

    voice_text = format_voice_time(stats.voice_seconds)
    messages_text = format_number(stats.messages)

    draw.text(
        (VOICE_X, VOICE_Y),
        voice_text,
        font=value_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )

    draw.text(
        (MESSAGES_X, MESSAGES_Y),
        messages_text,
        font=value_font,
        fill=STATS_VALUE_COLOR,
        anchor="mm"
    )


# =========================
# MAIN
# =========================
async def create_profile_card(
    user: discord.Member,
    stats: ProfileStats
) -> BytesIO:
    card = Image.open(PROFILE_TEMPLATE).convert("RGBA")

    avatar = await prepare_avatar(user)
    card.paste(avatar, (AVATAR_X, AVATAR_Y), avatar)

    draw_name_block(card, user)
    draw_roles(card, user)
    draw_balance_badge(card, stats)
    draw_level_block(card, stats)
    draw_exp_stats(card, stats)
    draw_activity_stats(card, stats)

    buffer = BytesIO()
    card.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer