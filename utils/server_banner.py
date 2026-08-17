from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent

BANNER_PATH = BASE_DIR / "assets" / "content.png"
FONT_PATH = BASE_DIR / "assets" / "Merriweather_24pt-Regular.ttf"


def create_server_banner(
    online_count: int,
    member_count: int
) -> bytes:
    image = Image.open(BANNER_PATH).convert("RGBA")

    draw = ImageDraw.Draw(image)

    online_font = ImageFont.truetype(
        FONT_PATH,
        42
    )

    members_font = ImageFont.truetype(
        FONT_PATH,
        25
    )

    gold = (212, 181, 128, 255)
    muted_gold = (166, 143, 105, 255)

    online_text = f"{online_count} В САДУ"
    members_text = f"{member_count} ДУШ"

    x = 1050
    y = 690

    draw.text(
        (x, y),
        online_text,
        font=online_font,
        fill=gold
    )

    draw.text(
        (x, y + 55),
        members_text,
        font=members_font,
        fill=muted_gold
    )

    buffer = BytesIO()

    image.convert("RGB").save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()