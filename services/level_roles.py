import discord

from config.roles import LEVEL_ROLES


def get_level_role_name(
    level: int,
) -> str | None:
    milestone = get_current_level_role(level)

    if milestone is None:
        return None

    return milestone[1]


def get_current_level_role(
    level: int,
) -> tuple[int, str] | None:
    available_levels = [
        required_level
        for required_level in LEVEL_ROLES
        if level >= required_level
    ]

    if not available_levels:
        return None

    milestone_level = max(available_levels)

    return (
        milestone_level,
        LEVEL_ROLES[milestone_level],
    )


def get_next_level_role(
    level: int,
) -> tuple[int, str] | None:
    upcoming_levels = [
        required_level
        for required_level in LEVEL_ROLES
        if required_level > level
    ]

    if not upcoming_levels:
        return None

    milestone_level = min(upcoming_levels)

    return (
        milestone_level,
        LEVEL_ROLES[milestone_level],
    )


async def sync_level_role(
    member: discord.Member,
    level: int,
) -> discord.Role | None:
    """
    Синхронизирует только юбилейную роль активности.

    Конкретные уровни и названия ролей задаются в config.roles.
    Если список пока пуст, функция безопасно ничего не делает.
    У участника остаётся только самая высокая доступная milestone-роль.
    """

    target_name = get_level_role_name(level)
    level_role_names = set(LEVEL_ROLES.values())

    current_level_roles = [
        role
        for role in member.roles
        if role.name in level_role_names
    ]

    target_role = None

    if target_name is not None:
        target_role = discord.utils.get(
            member.guild.roles,
            name=target_name,
        )

        if target_role is None:
            raise RuntimeError(
                f"Не найдена роль {target_name}"
            )

    roles_to_remove = [
        role
        for role in current_level_roles
        if role != target_role
    ]

    if roles_to_remove:
        await member.remove_roles(
            *roles_to_remove,
            reason="LOST EDEN activity milestone role update",
        )

    if (
        target_role is not None
        and target_role not in member.roles
    ):
        await member.add_roles(
            target_role,
            reason="LOST EDEN activity milestone",
        )

    return target_role
