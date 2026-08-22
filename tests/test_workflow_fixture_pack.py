from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "fixtures" / "workflow" / "workflow_test_pack.json"
SCRIPT_PATH = ROOT / "scripts" / "materialize_workflow_fixture.py"


def load_materializer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("workflow_fixture_materializer", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_pack_is_synthetic_and_has_eleven_steps() -> None:
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    assert pack["synthetic_only"] is True
    assert pack["contains_real_customer_data"] is False
    assert pack["settlement_execution_authorized"] is False
    assert pack["human_approval_required"] is True
    assert len(pack["cases"]) == 6
    for fixture_path in pack["supporting_fixtures"].values():
        assert (PACK_PATH.parent / fixture_path).resolve().is_file()

    for scenario in pack["cases"]:
        assert len(scenario["expected"]["steps"]) == 11
        assert scenario["expected"]["steps"][-1] == "PENDING_HUMAN_REVIEW"
        assert scenario["expected"]["automatic_settlement"] is False
        for finding in scenario["expected"]["findings"]:
            assert set(finding) == {
                "rule_id",
                "ucp_article",
                "expected_value",
                "actual_value",
                "evidence",
            }


def test_materializer_applies_incomplete_and_conflict_mutations() -> None:
    materializer = load_materializer()

    incomplete = materializer.materialize("WF-002-INCOMPLETE")
    incomplete_names = {item["filename"] for item in incomplete["documents"]}
    assert "insurance_certificate.pdf" not in incomplete_names
    assert len(incomplete["documents"]) == 6

    conflict = materializer.materialize("WF-003-ART14D-CONFLICT")
    packing_list = next(
        item for item in conflict["documents"] if item["filename"] == "packing_list.pdf"
    )
    assert packing_list["fields"]["total_quantity"]["value"] == 480
    assert conflict["synthetic_test_metadata"]["human_approval_required"] is True


def test_all_materialized_sources_and_sample_document_sets_exist() -> None:
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    materializer = load_materializer()

    for scenario in pack["cases"]:
        assert (PACK_PATH.parent / scenario["source_fixture"]).resolve().is_file()
        sample_dir = (PACK_PATH.parent / scenario["sample_documents"]).resolve()
        assert sample_dir.is_dir()
        assert list(sample_dir.glob("*.pdf"))
        materialized = materializer.materialize(scenario["scenario_id"])
        assert materialized["case_id"] == scenario["case_id"]
        assert materialized["documents"]
