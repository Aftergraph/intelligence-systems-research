import jev_engineering as jev


def test_v217_version():
    assert tuple(map(int, jev.__version__.split('.'))) >= (2, 17, 0)


def test_v217_campaign_readiness_public_api():
    for name in (
        'CompletionReadinessPolicy', 'CompletionConditionReport', 'CompletionReadinessReport',
        'TurnBudgetRecommendation', 'PoweredCampaignPlan', 'analyze_completion_readiness',
        'recommend_turn_budgets', 'plan_powered_campaign',
    ):
        assert hasattr(jev, name), name