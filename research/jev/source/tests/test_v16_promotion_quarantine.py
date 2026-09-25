from pathlib import Path
from jev_engineering.learning import LearningCandidate, LearningState
from jev_engineering.shadow_runtime import PromotionRegistry


def test_promotion_registry_quarantine_removes_active_route(tmp_path: Path) -> None:
    path = tmp_path / 'routes.json'
    registry = PromotionRegistry(path=path)
    candidate = LearningCandidate('c', 'safe_to_run', 'frontier', 'jev', state=LearningState.PROMOTED)
    registry.register(candidate)
    assert registry.preferred('safe_to_run') == 'jev'
    registry.quarantine('safe_to_run', reason='post-promotion regression')
    assert registry.preferred('safe_to_run') is None
    assert registry.quarantine_record('safe_to_run')['reason'] == 'post-promotion regression'
    loaded = PromotionRegistry.load(path)
    assert loaded.preferred('safe_to_run') is None
    assert loaded.quarantine_record('safe_to_run') is not None
