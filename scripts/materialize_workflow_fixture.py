from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "fixtures" / "workflow" / "workflow_test_pack.json"


def load_pack() -> dict[str, Any]:
    return dict(json.loads(PACK_PATH.read_text(encoding="utf-8")))


def get_scenario(scenario_id: str) -> dict[str, Any]:
    pack = load_pack()
    for scenario in pack["cases"]:
        if scenario["scenario_id"] == scenario_id:
            return dict(scenario)
    available = ", ".join(item["scenario_id"] for item in pack["cases"])
    raise ValueError(f"Unknown scenario {scenario_id!r}. Available: {available}")


def materialize(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    source_path = (PACK_PATH.parent / scenario["source_fixture"]).resolve()
    fixture = copy.deepcopy(json.loads(source_path.read_text(encoding="utf-8")))
    fixture["case_id"] = scenario["case_id"]

    for mutation in scenario.get("mutations", []):
        operation = mutation["operation"]
        if operation == "remove_document":
            fixture["documents"] = [
                document
                for document in fixture["documents"]
                if document["filename"] != mutation["filename"]
            ]
            continue
        if operation == "set_field":
            document = next(
                item
                for item in fixture["documents"]
                if item["filename"] == mutation["filename"]
            )
            document["fields"][mutation["field"]] = {
                "value": mutation["value"],
                "confidence": mutation["confidence"],
                "page": mutation["page"],
            }
            continue
        raise ValueError(f"Unsupported mutation operation: {operation}")

    fixture["synthetic_test_metadata"] = {
        "scenario_id": scenario["scenario_id"],
        "name": scenario["name"],
        "presenting_ibu": scenario["presenting_ibu"],
        "sample_documents": scenario["sample_documents"],
        "expected": scenario["expected"],
        "settlement_execution_authorized": False,
        "human_approval_required": True,
    }
    if "registry_setup" in scenario:
        fixture["synthetic_test_metadata"]["registry_setup"] = scenario["registry_setup"]
    return fixture


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize a synthetic TradeSentry workflow fixture"
    )
    parser.add_argument("--scenario", help="Scenario ID from the workflow test pack")
    parser.add_argument("--output", type=Path, help="Destination JSON file")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    args = parser.parse_args()

    if args.list:
        for scenario in load_pack()["cases"]:
            print(f"{scenario['scenario_id']}: {scenario['name']}")
        return
    if not args.scenario or not args.output:
        parser.error("--scenario and --output are required unless --list is used")

    result = materialize(args.scenario)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Materialized {args.scenario} to {args.output}")


if __name__ == "__main__":
    main()
