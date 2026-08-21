# Sprint 9 Failure Report

Date: 2026-08-21

## Final status

No unresolved evaluation failures remain. All fourteen labeled cases and all five
release blockers pass. The full repository suite passes.

## Resolved findings

### Prompt-injection attempt lacked a dedicated audit signal

- Observed during pre-test mapping for Case L.
- Root cause: planner input already excluded raw text, but document processing did
  not record detection of instruction-like content.
- Fix: deterministic pattern detection now produces only a SHA-256 fingerprint,
  stores an `AGENT_DECISION` audit reference, and adds a human-review advisory.
- Safety: raw document text is neither logged nor stored in the audit payload.

### Low-confidence and conflicting DNA evidence did not independently require review

- Observed during pre-test mapping for Cases I and J.
- Root cause: flags were retained in Transaction DNA but were not converted into
  explicit evidence and review-gate inputs.
- Fix: advisory low-confidence evidence and review-level conflict evidence are now
  emitted; deterministic risk assessment routes both to human review.

### Specified fuzzy sanctions example initially produced no match

- Observed on the first Case N fixture check.
- Root cause: the bundled synthetic list had no similar synthetic party.
- Fix: added a clearly synthetic near-name source record. The result is
  `POSSIBLE_MATCH`, never `CONFIRMED_SOURCE_MATCH`, and explicitly requires human
  determination.

### Tool-timeout assertion initially looked in the wrong evidence channel

- Observed in the first Case K test run.
- Root cause: the runner correctly returned typed `DATA_UNAVAILABLE` with a timeout
  caveat, while the draft assertion expected an orchestrator error string.
- Fix: the test now checks the typed result and its evidence caveat. No production
  behavior change was needed.

## Known evaluation limitations

- Synthetic and pre-extracted documents cannot establish production OCR accuracy.
- Mock price, sanctions, vessel, and entity datasets are intentionally small.
- No live AWS staging smoke test or real external-provider cost measurement was run.
- ClamAV remains a production stub as documented in the Sprint 8 threat model.
- Risk weights and similarity thresholds remain prototype demo values.
