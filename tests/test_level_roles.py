import services.level_roles as level_roles


def test_milestones_are_empty_until_configured(monkeypatch):
    monkeypatch.setattr(level_roles, "LEVEL_ROLES", {})

    assert level_roles.get_current_level_role(50) is None
    assert level_roles.get_next_level_role(1) is None
    assert level_roles.get_level_role_name(50) is None


def test_current_and_next_milestone(monkeypatch):
    monkeypatch.setattr(
        level_roles,
        "LEVEL_ROLES",
        {
            10: "First",
            25: "Second",
            50: "Third",
        },
    )

    assert level_roles.get_current_level_role(24) == (10, "First")
    assert level_roles.get_next_level_role(24) == (25, "Second")
    assert level_roles.get_level_role_name(24) == "First"


def test_highest_milestone_has_no_next_role(monkeypatch):
    monkeypatch.setattr(
        level_roles,
        "LEVEL_ROLES",
        {
            10: "First",
            25: "Second",
        },
    )

    assert level_roles.get_current_level_role(30) == (25, "Second")
    assert level_roles.get_next_level_role(30) is None
