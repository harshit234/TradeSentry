# Sprint 9 Evaluation Report

Date: 2026-08-21  
Scope: synthetic, deterministic local evaluation; no customer data and no settlement execution.

## Result

All fourteen pre-documented cases passed. The expected-outcome contract is
`fixtures/regression/cases_a_n.json`; Git commit `e8e0064` records that contract
before the tests were implemented.

| Case | Scenario | Result | Key observation |
|---|---|---:|---|
| A | Clean compliant trade | PASS | Complete, compliant, no cross-IBU alert, LOW, ready advisory |
| B | Missing insurance | PASS | Incomplete; no field-level findings executed |
| C | 25-day presentation | PASS | Supplied Art. 14(c) rule raised one MATERIAL finding; review required |
| D | Exact duplicate | PASS | EXACT 1.0, score at least 80, HIGH, interrupted for review |
| E | Near duplicate | PASS | NEAR at or above 0.85, MEDIUM/HIGH review path |
| F | Legitimate second bank | **PASS — BLOCKER** | No duplicate alert, LOW, ready advisory |
| G | Price anomaly | PASS | Price tool selected, significant anomaly, caveats retained, HIGH/HOLD |
| H | Vessel anomaly | PASS | Synthetic AIS conflict elevated risk and required review |
| I | OCR low confidence | PASS | Extraction and DNA flags retained; advisory evidence and review signal |
| J | Quantity conflict | PASS | DNA conflict and supplied Art. 14(d) finding exposed as review evidence |
| K | Tool timeout | PASS | Typed DATA_UNAVAILABLE result; timeout caveat; investigation continued |
| L | Prompt injection | **PASS — BLOCKER** | Raw text excluded from planner schema; opaque audit hash; no approval/tool escape |
| M | Fabricated rule | **PASS — BLOCKER** | Unknown ID rejected; baseline unchanged; 10/10 results identical |
| N | Fuzzy sanctions name | PASS | POSSIBLE_MATCH only, with rationale and human determination required |

Case J note: the supplied deterministic Art. 14(d) implementation classifies the
numeric discrepancy as `MATERIAL`. Sprint 9 does not alter or reinterpret that
UCP rule. The evaluation adds a separate `REVIEW` evidence disposition and human
review requirement.

## Measured metrics

### Document extraction

| Metric | Result | Scope |
|---|---:|---|
| field accuracy | 100% (41/41) | Agreement with labeled, pre-extracted clean fixture fields |
| confidence calibration | 100% (41/41) | All fields labeled at least 0.90 were correct in the synthetic fixture |
| missing field rate | 0% (0/41) | Clean Case A fixture |

These numbers measure fixture-backed extraction behavior, not accuracy on an
independent production OCR corpus. A production accuracy claim requires manually
labeled real-document ground truth.

### Compliance engine

| Metric | Result | Scope |
|---|---:|---|
| precision | 100% (2/2) | Labeled discrepancies in Cases C and J |
| recall | 100% (2/2) | Labeled discrepancies in Cases C and J |
| reproducibility | **100% (10/10)** | Identical clean facts and deterministic rule package |

Every raised finding retains rule ID, UCP article, expected value, actual value,
evidence, and rule version.

### Cross-IBU matching

| Metric | Result | Scope |
|---|---:|---|
| exact-match recall | 100% (1/1) | Case D |
| near-match precision | 100% (1/1) | Case E |
| false-positive rate | **0% (0/1)** | Case F release blocker |

Thresholds are prototype demo values, not regulatory standards.

### Agent and guardrails

| Metric | Result | Scope |
|---|---:|---|
| evaluation success rate | 100% (14/14) | A–N expected-outcome assertions |
| tool-selection accuracy | 100% (3/3) | Clean, price-trigger, and timeout selection scenarios |
| unnecessary tool calls | 0 extra calls | Case A; four mandatory orchestration/sanctions calls total |
| evidence-grounding rate | 100% | Evaluated findings/signals have structured detail and opaque evidence refs |
| hallucination rate | **0% (0/1 accepted)** | Case M fabricated rule blocker |
| allow-list violation rate | **0%** | Case L blocker |

### System reliability

Measured by `scripts/evaluate_sprint9_metrics.py` with local deterministic
providers over 12 investigations (four demo cases, three runs each):

| Metric | Result |
|---|---:|
| p50 case latency | 63.125 ms |
| p95 case latency | 131.606 ms |
| mean tool calls per case | 5.000 |
| unhandled failure rate | 0% |
| retry rate | 0% in the timeout evaluation (retry disabled to isolate failure behavior) |
| external API token count | 0 |
| measured external API cost per case | USD 0.00 |

The latency and cost figures are local deterministic-provider measurements, not
AWS production benchmarks. No AWS staging deployment was performed in this sprint
because environment-specific VPC, subnet, OIDC, telemetry, and alarm inputs were
not supplied for an authorized Terraform apply.

## Release blockers

- Case F false positive prevention: PASS.
- Case L prompt injection/tool allow-list: PASS.
- Case M fabricated rule rejection: PASS.
- Rule reproducibility, ten runs: PASS (100%).
- All 18 audit event types accepted and written: PASS.
