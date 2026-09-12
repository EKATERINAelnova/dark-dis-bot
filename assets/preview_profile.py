import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from utils.profile_card_v2 import (
    ProfileCardData,
    create_profile_card_v2,
)


AVATAR_PATH = (
    PROJECT_ROOT
    / "assets"
    / "preview_avatar.png"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "preview_template_v2.png"
)

class PreviewAvatar:
    async def read(self):
        return AVATAR_PATH.read_bytes()


class PreviewUser:
    display_name = "дышите носиком.ina"
    name = "smalltalk_eater"
    discriminator = "0"
    display_avatar = PreviewAvatar()


async def main():
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

    os.startfile(
        OUTPUT_PATH.resolve()
    )


asyncio.run(main())