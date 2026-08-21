# Demo runbook

## Pre-flight

1. Run `make health-check`; confirm all five dependencies plus overall status are `ok` and version is the submitted git SHA.
2. Run `make seed-demo`; it must finish in under 30 seconds.
3. Issue separate 30-minute officer tokens with `make demo-token IBU_ID=IBU-A` and `IBU-B`; never paste tokens into notes or chat.
4. Confirm A, B, and D appear for IBU-A and C appears for IBU-B.
5. Open one PDF, inspect the agent timeline and AWS badge, and test the backup device.
6. Play each local backup video before entering the room.
7. Chrome, zoom 100%, light mode, notifications disabled.

## Demo 1 — clean trade (two minutes)

Open `DEMO-CASE-A`. Show seven high-confidence documents, compliant UCP result,
Cross-IBU `NO_MATCH`, at most four calls, LOW risk, and readiness advisory. Say:
“Clean case. Seven documents. Deterministic compliance, cross-IBU check, full
audit trail.” Quote measured duration only if visible.

## Demo 2 — duplicate-financing signal (four minutes)

Open `DEMO-CASE-B`. Show exact normalized B/L match in IBU-C, similarity 1.0,
matched fields, measured DynamoDB latency, HIGH risk, HOLD, and the officer form.
Say: “Same B/L, different bank. The registry caught the signal before the bank's
settlement workflow. No consequential action occurs without the officer.”

## Demo 3 — TBML price signal (three minutes)

Switch to the IBU-B token and open `DEMO-CASE-C`. Contrast UCP compliant with
the significant USD 810/MT price signal, USD 340/MT reference P90, +138.24%,
source attribution, caveats, HIGH risk, and HOLD. Say: “A review signal, not a
fraud verdict. The officer decides.”

## Demo 4 — legitimate second bank (two minutes)

Return to IBU-A and open `DEMO-CASE-D`. Show `NO_MATCH`, measured similarity
approximately 0.34, LOW risk, readiness advisory, and no high-severity alert.
Say: “Same exporter, different shipment. Trust requires accuracy in both
directions.”

## Fallback

If staging is unreachable, switch immediately to the matching backup video and
narrate. Do not live-debug. Use the printed evaluation report for Q&A. After any
reset, run `make health-check` again.
