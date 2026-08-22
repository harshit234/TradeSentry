# Synthetic 11-step workflow test pack

`workflow_test_pack.json` defines six fully synthetic scenarios for testing the
TradeSentry investigation workflow. It references the existing synthetic PDF and
pre-extracted fixtures, then applies small deterministic mutations where needed.

Scenarios cover:

1. Complete clean presentation
2. Missing required document
3. Cross-document quantity conflict under the existing Article 14(d) rule
4. Exact duplicate-financing signal across IBUs
5. Price-corridor and AIS vessel investigation signals
6. Legitimate distinct presentation at another IBU

Materialize a case without accessing AWS, a database, or settlement infrastructure:

```powershell
python scripts/materialize_workflow_fixture.py --scenario WF-003-ART14D-CONFLICT --output .tmp/synthetic-case.json
```

List scenario IDs:

```powershell
python scripts/materialize_workflow_fixture.py --list
```

The generated JSON is suitable for deterministic extraction/compliance test setup.
The `sample_documents` path identifies the matching upload set for UI/OCR testing.
Risk expectations are prototype investigation signals only. Every scenario ends at
the human-review gate; none authorizes or simulates settlement.
