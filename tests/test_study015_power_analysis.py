from experiments.study015.power_analysis import (
    draft_plan,
    paired_binary_planning_n,
    paired_continuous_planning_n,
)


def test_smaller_binary_effect_requires_more_pairs():
    medium = paired_binary_planning_n(
        net_difference=0.15, discordant_rate=0.30, alpha=0.00625, power=0.80
    )
    small = paired_binary_planning_n(
        net_difference=0.10, discordant_rate=0.30, alpha=0.00625, power=0.80
    )
    assert small > medium > 0


def test_smaller_continuous_effect_requires_more_pairs():
    assert paired_continuous_planning_n(
        standardized_effect=0.25, alpha=0.00625, power=0.80
    ) > paired_continuous_planning_n(
        standardized_effect=0.50, alpha=0.00625, power=0.80
    )


def test_draft_plan_is_explicitly_not_frozen():
    plan = draft_plan()
    assert plan["status"] == "DRAFT_NOT_FROZEN"
    assert plan["target_power"] == 0.80
    assert "freeze" in plan["freeze_requirement"].lower()
