"""Zero-network contract probe for the optional TypeSafe SDK pin."""

from pathlib import Path
import importlib.metadata
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.system_one_acceleration.client import (
    build_sdk_questions,
    load_frozen_contracts,
)


def main() -> int:
    import typesafe_sdk

    version = importlib.metadata.version("typesafe-sdk")
    if version != "0.7.0":
        raise SystemExit(f"unexpected typesafe-sdk version: {version}")

    contracts = load_frozen_contracts(
        ROOT / "data" / "jar_exp_0014_question_contracts_v01.json"
    )
    built = build_sdk_questions(contracts, sdk=typesafe_sdk)

    if set(built) != set(contracts):
        raise SystemExit("SDK question set does not match frozen contracts")

    expected_types = {
        "route_model": typesafe_sdk.Choice,
        "route_tool_family": typesafe_sdk.Choice,
        "continue_loop": typesafe_sdk.Noul,
        "result_sufficient": typesafe_sdk.Noul,
        "needs_human": typesafe_sdk.Noul,
        "risk_level": typesafe_sdk.Score,
        "retryable_failure": typesafe_sdk.Noul,
        "evidence_conflict": typesafe_sdk.Noul,
    }
    for key, expected_type in expected_types.items():
        if not isinstance(built[key], expected_type):
            raise SystemExit(f"{key}: unexpected SDK question type")

    print(f"PASS: typesafe-sdk {version}; {len(built)} frozen contracts constructed")
    print("NETWORK_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
