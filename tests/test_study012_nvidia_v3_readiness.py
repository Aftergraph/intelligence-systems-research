from providers.nvidia import NvidiaProvider
from experiments.live_benchmark.study012_nvidia_v3_readiness import TARGETS
def test_v3_models_are_distinct_and_catalog_pinned():
 models={m for m,_,_,_ in TARGETS}
 assert len(models)==3
 supported=NvidiaProvider(api_key="x").get_supported_models()
 assert models.issubset(set(supported))
def test_v3_probe_is_exactly_nine_calls():
 assert len(TARGETS)==3
