import os

import discord


VERIFIED_ROLE_ENV = "VERIFIED_ROLE_ID"


def get_verified_role_id() -> int | None:
    raw_role_id = os.getenv(
        VERIFIED_ROLE_ENV
    )

    if raw_role_id is None:
        return None

    raw_role_id = raw_role_id.strip()

    if not raw_role_id.isdigit():
        raise RuntimeError(
            f"{VERIFIED_ROLE_ENV} должен содержать ID роли"
        )

    return int(raw_role_id)


async def set_verified_role(
    member: discord.Member,
    verified: bool,
) -> discord.Role | None:
    """
    Добавляет или снимает единственную роль верификации.

    Логика самой верификации живёт отдельно. Этот сервис отвечает
    только за синхронизацию Discord-роли после её результата.
    """

    role_id = get_verified_role_id()

    if role_id is None:
        return None

    role = member.guild.get_role(
        role_id
    )

    if role is None:
        raise RuntimeError(
            f"Роль верификации с ID {role_id} не найдена"
        )

    if verified:
        if role not in member.roles:
            await member.add_roles(
                role,
                reason="LOST EDEN verification passed",
            )
    elif role in member.roles:
        await member.remove_roles(
            role,
            reason="LOST EDEN verification revoked",
        )

    return role
