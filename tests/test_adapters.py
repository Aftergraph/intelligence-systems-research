import os
import sys
import yaml

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from adapters.native_adapter import NativeRuntimeAdapter
from adapters.langgraph_adapter import LangGraphAdapter
from adapters.autogen_adapter import AutoGenAdapter

def test_cross_runtime_portability():
    mission_path = os.path.join(workspace, "examples", "mission.release.yaml")
    with open(mission_path, "r", encoding="utf-8") as f:
        mission_doc = yaml.safe_load(f)

    adapters = [
        NativeRuntimeAdapter(),
        LangGraphAdapter(),
        AutoGenAdapter()
    ]

    invariants = []
    for adapter in adapters:
        compiled = adapter.compile_mission(mission_doc)
        inv = adapter.extract_semantic_invariants(compiled)
        invariants.append((adapter.name, inv))
        print(f"Compiled successfully with {adapter.name}: {inv['objective'][:40]}...")

    # Assert cross-runtime semantic equivalence (0% semantic deviation)
    ref_name, ref_inv = invariants[0]
    for name, inv in invariants[1:]:
        assert inv["objective"] == ref_inv["objective"], f"Objective mismatch between {ref_name} and {name}"
        assert inv["criteria"] == ref_inv["criteria"], f"Criteria mismatch between {ref_name} and {name}"
        assert inv["recovery_limit"] == ref_inv["recovery_limit"], f"Recovery limit mismatch between {ref_name} and {name}"
        print(f"SUCCESS: {name} semantically identical to {ref_name}.")

    print("SUCCESS: Phase E Cross-Runtime Portability Gate passed with 0% semantic deviation.")

if __name__ == "__main__":
    test_cross_runtime_portability()
