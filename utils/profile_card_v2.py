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


# Текущие координаты профиля. Не менять без ручной подгонки шаблона.
AVATAR_CENTER = (301, 310)
AVATAR_SIZE = 345
AVATAR_X = AVATAR_CENTER[0] - AVATAR_SIZE // 2
AVATAR_Y = AVATAR_CENTER[1] - AVATAR_SIZE // 2

DISPLAY_NAME_POS = (797, 216)
DISPLAY_NAME_MAX_WIDTH = 390

USERNAME_POS = (716, 289)
USERNAME_MAX_WIDTH = 390

VERIFICATION_CENTER = (654, 538)
VERIFICATION_MAX_WIDTH = 135

MILESTONE_CENTER = (835, 535)
MILESTONE_MAX_WIDTH = 150

CASES_CENTER = (1058, 524)
CASES_MAX_WIDTH = 90

LEVEL_CENTER = (1389, 277)
RANK_CENTER = (1742, 277)

TOTAL_XP_CENTER = (1389, 448)
XP_NEXT_CENTER = (1742, 448)

BALANCE_CENTER = (1592, 525)

VOICE_CENTER = (755, 635)
MESSAGES_CENTER = (1520, 635)


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
        return f"{hours} ч {minutes:02} мин"

    return f"{minutes} мин"


def verification_value(status: str) -> str:
    if status == "verified":
        return "ПРОЙДЕНА"

    if status == "unconfigured":
        return "НЕ НАСТРОЕНА"

    return "ОЖИДАЕТ"


def get_profile_badges(
    data: ProfileCardData,
) -> list[tuple[str, str]]:
    milestone = data.milestone_name or "НЕ ОТКРЫТА"

    return [
        (
            verification_value(data.verification_status),
            "verification",
        ),
        (
            milestone,
            "milestone",
        ),
        (
            str(data.eden_cases),
            "cases",
        ),
    ]


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    start_size: int,
    max_width: int,
    min_size: int = 12,
) -> ImageFont.FreeTypeFont:
    size = start_size

    while size >= min_size:
        font = ImageFont.truetype(
            font_path,
            size,
        )
        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )

        if bbox[2] - bbox[0] <= max_width:
            return font

        size -= 1

    return ImageFont.truetype(
        font_path,
        min_size,
    )


def draw_centered_text(
    card: Image.Image,
    center: tuple[int, int],
    text: str,
    *,
    max_width: int,
    start_size: int = 22,
    min_size: int = 12,
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


def draw_left_text(
    card: Image.Image,
    position: tuple[int, int],
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
        position,
        text,
        font=font,
        fill=color,
        anchor="lm",
    )


async def prepare_avatar(
    user: discord.Member,
) -> Image.Image:
    avatar_bytes = await user.display_avatar.read()
    avatar = Image.open(
        BytesIO(avatar_bytes)
    ).convert("RGBA")

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
        (
            0,
            0,
            AVATAR_SIZE - 1,
            AVATAR_SIZE - 1,
        ),
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


def username_text(
    user: discord.Member,
) -> str:
    if user.discriminator != "0":
        return (
            f"@{user.name}"
            f"#{user.discriminator}"
        )

    return f"@{user.name}"


def draw_identity(
    card: Image.Image,
    user: discord.Member,
) -> None:
    draw_left_text(
        card,
        DISPLAY_NAME_POS,
        user.display_name,
        max_width=DISPLAY_NAME_MAX_WIDTH,
        start_size=22,
        min_size=15,
        font_path=FONT_PATH,
    )

    draw_left_text(
        card,
        USERNAME_POS,
        username_text(user),
        max_width=USERNAME_MAX_WIDTH,
        start_size=21,
        min_size=13,
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
        verification_value(
            data.verification_status
        ),
        max_width=VERIFICATION_MAX_WIDTH,
        start_size=12,
        min_size=8,
        font_path=FONT_PATH,
    )

    draw_centered_text(
        card,
        MILESTONE_CENTER,
        data.milestone_name or "НЕ ОТКРЫТА",
        max_width=MILESTONE_MAX_WIDTH,
        start_size=12,
        min_size=8,
        font_path=FONT_PATH,
    )

    draw_centered_text(
        card,
        CASES_CENTER,
        str(data.eden_cases),
        max_width=CASES_MAX_WIDTH,
        start_size=17,
        min_size=12,
    )


def draw_progress_values(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw_centered_text(
        card,
        LEVEL_CENTER,
        str(data.level),
        max_width=85,
        start_size=28,
        min_size=20,
    )

    draw_centered_text(
        card,
        RANK_CENTER,
        f"#{data.rank}",
        max_width=95,
        start_size=27,
        min_size=19,
    )

    draw_centered_text(
        card,
        TOTAL_XP_CENTER,
        format_number(data.total_xp),
        max_width=145,
        start_size=17,
        min_size=12,
    )

    draw_centered_text(
        card,
        XP_NEXT_CENTER,
        format_number(
            data.xp_to_next_level
        ),
        max_width=145,
        start_size=17,
        min_size=12,
    )

    draw_centered_text(
        card,
        BALANCE_CENTER,
        format_number(data.currency),
        max_width=245,
        start_size=20,
        min_size=14,
    )


def draw_activity_values(
    card: Image.Image,
    data: ProfileCardData,
) -> None:
    draw_centered_text(
        card,
        VOICE_CENTER,
        format_voice_time(
            data.voice_seconds
        ),
        max_width=205,
        start_size=18,
        min_size=12,
    )

    draw_centered_text(
        card,
        MESSAGES_CENTER,
        format_number(data.messages),
        max_width=170,
        start_size=18,
        min_size=12,
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
            f"получено "
            f"{card.size[0]}x{card.size[1]}"
        )

    avatar = await prepare_avatar(user)
    card.paste(
        avatar,
        (AVATAR_X, AVATAR_Y),
        avatar,
    )

    draw_identity(
        card,
        user,
    )
    draw_statuses(
        card,
        data,
    )
    draw_progress_values(
        card,
        data,
    )
    draw_activity_values(
        card,
        data,
    )

    buffer = BytesIO()
    card.save(
        buffer,
        format="PNG",
    )
    buffer.seek(0)

    return buffer
