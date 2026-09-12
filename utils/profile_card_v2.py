from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps


BASE_DIR = Path(__file__).resolve().parents[1]
PROFILE_TEMPLATE_V2 = BASE_DIR / "assets" / "profile_template_v2.png"
FONT_PATH = BASE_DIR / "assets" / "Merriweather_24pt-Regular.ttf"
FONT_PATH2 = BASE_DIR / "assets" / "Marcellus-Regular.ttf"

TEMPLATE_SIZE = (1983, 793)
TEXT_COLOR = "#E9D4B7"
SECONDARY_TEXT_COLOR = "#C8AE91"

# =========================
# AVATAR
# =========================
# Центр круга шаблона примерно (292, 302).
# Размер немного меньше внутреннего золотого кольца,
# чтобы аватар не залезал на декоративную рамку.
AVATAR_SIZE = 326
AVATAR_X = 129
AVATAR_Y = 139


# =========================
# IDENTITY
# =========================
DISPLAY_NAME_CENTER = (835, 203)
DISPLAY_NAME_MAX_WIDTH = 500

USERNAME_CENTER = (836, 285)
USERNAME_MAX_WIDTH = 440


# =========================
# STATUS VALUES
# =========================
VERIFICATION_CENTER = (636, 524)
VERIFICATION_MAX_WIDTH = 150

MILESTONE_CENTER = (829, 524)
MILESTONE_MAX_WIDTH = 160

CASES_CENTER = (1025, 524)
CASES_MAX_WIDTH = 110


# =========================
# PROGRESS VALUES
# =========================
LEVEL_CENTER = (1347, 268)
RANK_CENTER = (1686, 268)

TOTAL_XP_CENTER = (1348, 416)
XP_NEXT_CENTER = (1686, 416)

BALANCE_CENTER = (1594, 518)


# =========================
# ACTIVITY VALUES
# =========================
# Для нижнего блока используем одну baseline, а не mm-центрирование.
# Так "0 min" и "1" стоят визуально на одной линии.
ACTIVITY_BASELINE_Y = 655
VOICE_CENTER_X = 752
MESSAGES_CENTER_X = 1544


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


def format_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_voice_time(seconds: int) -> str:
    total_minutes = max(0, seconds) // 60
    hours, minutes = divmod(total_minutes, 60)

    if hours > 0:
        return f"{hours} h {minutes:02} min"

    return f"{minutes} min"


def verification_value(status: str) -> str:
    if status == "verified":
        return "VERIFIED"

    if status == "unconfigured":
        return "NOT SET"

    return "PENDING"


def get_profile_badges(
    data: ProfileCardData,
) -> list[tuple[str, str]]:
    milestone = data.milestone_name or "NO MILESTONE"

    return [
        (verification_value(data.verification_status), "verification"),
        (milestone, "milestone"),
        (f"CASES · {data.eden_cases}", "cases"),
    ]


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    start_size: int,
    max_width: int,
    min_size: int = 14,
) -> ImageFont.FreeTypeFont:
    size = start_size

    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)

        if bbox[2] - bbox[0] <= max_width:
            return font

        size -= 1

    return ImageFont.truetype(font_path, min_size)


def draw_centered_text(
    card: Image.Image,
    center: tuple[int, int],
    text: str,
    *,
    max_width: int,
    start_size: int = 25,
    min_size: int = 13,
    font_path: Path = FONT_PATH,
    color: str = TEXT_COLOR,
) -> None:
    draw = ImageDraw.Draw(card)

    font = fit_font(
        draw=draw,
        text=text,
        font_path=font_path,
        start_size=start_size,
        max_width=max_width,
        min_size=min_size,
    )

    draw.text(
        center,
        text,
        font=font,
        fill=color,
        anchor="mm",
    )


def draw_baseline_text(
    card: Image.Image,
    x: int,
    baseline_y: int,
    text: str,
    *,
    max_width: int,
    start_size: int,
    min_size: int,
    font_path: Path = FONT_PATH,
    color: str = TEXT_COLOR,
) -> None:
    draw = ImageDraw.Draw(card)

    font = fit_font(
        draw=draw,
        text=text,
        font_path=font_path,
        start_size=start_size,
        max_width=max_width,
        min_size=min_size,
    )

    draw.text(
        (x, baseline_y),
        text,
        font=font,
        fill=color,
        anchor="ms",
    )


async def prepare_avatar(
    user: discord.Member,
) -> Image.Image:
    avatar_bytes = await user.display_avatar.read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")

    avatar = ImageOps.fit(
        avatar,
        (AVATAR_SIZE, AVATAR_SIZE),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    mask = Image.new(
        "L",
        (AVATAR_SIZE, AVATAR_SIZE),
        0,
    )
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse(
        (0, 0, AVATAR_SIZE - 1, AVATAR_SIZE - 1),
        fill=255,
    )

    result = Image.new(
        "RGBA",
        (AVATAR_SIZE, AVATAR_SIZE),
        (0, 0, 0, 0),
    )
    result.paste(
        avatar,
        (0, 0),
        mask,
    )

    return result


def username_text(user: discord.Member) -> str:
    if user.discriminator != "0":
        return f"@{user.name}#{user.discriminator}"

    return f"@{user.name}"


def draw_identity(
    card: Image.Image,
    user: discord.Member,
) -> None:
    draw_centered_text(
        card,
        DISPLAY_NAME_CENTER,
        user.display_name,
        max_width=DISPLAY_NAME_MAX_WIDTH,
        start_size=31,
        min_size=18,
        font_path=FONT_PATH,
    )

    draw_centered_text(
        card,
        USERNAME_CENTER,
        username_text(user),
        max_width=USERNAME_MAX_WIDTH,
        start_size=20,
        min_size=14,
        font_path=FONT_PATH2,
        color=SECONDARY_TEXT_COLOR,
    )


def draw_statuses(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw_centered_text(
        card,
        VERIFICATION_CENTER,
        verification_value(data.verification_status),
        max_width=VERIFICATION_MAX_WIDTH,
        start_size=16,
        min_size=10,
    )

    draw_centered_text(
        card,
        MILESTONE_CENTER,
        data.milestone_name or "NOT OPENED",
        max_width=MILESTONE_MAX_WIDTH,
        start_size=15,
        min_size=9,
    )

    draw_centered_text(
        card,
        CASES_CENTER,
        str(data.eden_cases),
        max_width=CASES_MAX_WIDTH,
        start_size=23,
        min_size=15,
    )


def draw_progress_values(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw_centered_text(
        card,
        LEVEL_CENTER,
        str(data.level),
        max_width=95,
        start_size=37,
        min_size=24,
    )

    draw_centered_text(
        card,
        RANK_CENTER,
        f"#{data.rank}",
        max_width=105,
        start_size=34,
        min_size=22,
    )

    draw_centered_text(
        card,
        TOTAL_XP_CENTER,
        format_number(data.total_xp),
        max_width=150,
        start_size=21,
        min_size=14,
    )

    draw_centered_text(
        card,
        XP_NEXT_CENTER,
        format_number(data.xp_to_next_level),
        max_width=150,
        start_size=21,
        min_size=14,
    )

    draw_centered_text(
        card,
        BALANCE_CENTER,
        format_number(data.currency),
        max_width=260,
        start_size=23,
        min_size=15,
    )


def draw_activity_values(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw_baseline_text(
        card,
        VOICE_CENTER_X,
        ACTIVITY_BASELINE_Y,
        format_voice_time(data.voice_seconds),
        max_width=220,
        start_size=22,
        min_size=14,
    )

    draw_baseline_text(
        card,
        MESSAGES_CENTER_X,
        ACTIVITY_BASELINE_Y,
        format_number(data.messages),
        max_width=180,
        start_size=22,
        min_size=14,
    )


async def create_profile_card_v2(
    user: discord.Member,
    data: ProfileCardData,
) -> BytesIO:
    if not PROFILE_TEMPLATE_V2.exists():
        raise FileNotFoundError(
            "Не найден новый шаблон профиля: "
            "assets/profile_template_v2.png"
        )

    card = Image.open(
        PROFILE_TEMPLATE_V2
    ).convert("RGBA")

    if card.size != TEMPLATE_SIZE:
        raise RuntimeError(
            "profile_template_v2.png должен иметь размер "
            f"{TEMPLATE_SIZE[0]}x{TEMPLATE_SIZE[1]}, "
            f"получено {card.size[0]}x{card.size[1]}"
        )

    avatar = await prepare_avatar(user)
    card.paste(
        avatar,
        (AVATAR_X, AVATAR_Y),
        avatar,
    )

    draw_identity(card, user)
    draw_statuses(card, data)
    draw_progress_values(card, data)
    draw_activity_values(card, data)

    buffer = BytesIO()
    card.save(
        buffer,
        format="PNG",
    )
    buffer.seek(0)

    return buffer
