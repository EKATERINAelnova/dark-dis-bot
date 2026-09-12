import asyncio
import os
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from utils.profile_card_v2 import (
    ProfileCardData,
    create_profile_card_v2,
)


AVATAR_PATH = ASSETS_DIR / "preview_avatar.png"
OUTPUT_PATH = PROJECT_ROOT / "temp.png"


class PreviewAvatar:
    async def read(self) -> bytes:
        if AVATAR_PATH.exists():
            return AVATAR_PATH.read_bytes()

        image = Image.new(
            "RGB",
            (512, 512),
            "#4A3A35",
        )

        draw = ImageDraw.Draw(image)

        draw.ellipse(
            (56, 56, 456, 456),
            outline="#D7C09E",
            width=8,
        )

        draw.text(
            (256, 256),
            "PREVIEW",
            fill="#E9D4B7",
            anchor="mm",
        )

        buffer = BytesIO()
        image.save(
            buffer,
            format="PNG",
        )

        return buffer.getvalue()


class PreviewUser:
    display_name = "дышите носиком.ina"
    name = "smalltalk_eater"
    discriminator = "0"
    display_avatar = PreviewAvatar()


async def main() -> None:
    data = ProfileCardData(
        level=5,
        rank=1,
        currency=68,
        messages=1,
        voice_seconds=0,
        total_xp=1129,
        xp_to_next_level=371,
        eden_cases=5,
        verification_status="unconfigured",
        milestone_name=None,
    )

    image = await create_profile_card_v2(
        user=PreviewUser(),
        data=data,
    )

    OUTPUT_PATH.write_bytes(
        image.getvalue()
    )

    print(
        f"Готово: {OUTPUT_PATH.resolve()}"
    )

    if hasattr(os, "startfile"):
        os.startfile(
            OUTPUT_PATH.resolve()
        )


if __name__ == "__main__":
    asyncio.run(main())
