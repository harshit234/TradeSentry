# Hackathon pitch scripts

## Round 1 — three minutes

**0:00–0:30 · Problem.** Trade-finance fraud and trade-based money laundering
cost the global financial system tens of billions. GIFT City's IBUs validate LC
documents independently, so the same Bill of Lading can be presented to more
than one bank before either knows.

**0:30–0:50 · Gap.** Manual review under time pressure can miss cross-document
inconsistencies. UCP 600 checks are exacting, while no shared pre-settlement
signal exists across IBUs.

**0:50–1:30 · Product.** TradeSentry is an AI-assisted pre-settlement
intelligence layer. AWS Textract extracts structured facts. A constrained
LangGraph investigation selects approved read-only checks. Deterministic Python
evaluates versioned UCP rules, builds Transaction DNA, queries a DynamoDB
cross-IBU registry, and investigates price or vessel signals. The agent
investigates; humans authorize.

**1:30–1:50 · AWS.** The staging architecture uses AWS Textract, ECS, RDS,
DynamoDB, ElastiCache, S3, Secrets Manager, KMS, ECR, and CloudWatch, funded by
the hackathon AWS credits. Show `/health`; say only what the live response proves.

**1:50–2:20 · Demo headline.** Open Demo 2. “The same normalized B/L appeared
under IBU-C. DynamoDB returned an exact-match signal in the measured latency
shown here, before any settlement workflow. The officer sees which fields
matched and the evidence trail.” Never round the displayed latency down.

**2:20–2:40 · Credibility.** “The LLM does not decide compliance. It extracts
facts; a deterministic rule engine evaluates the reviewed UCP rule set. Same
inputs, same result, independently testable.”

**2:40–3:00 · Close.** “TradeSentry sits upstream of FCSS. It neither controls
nor integrates with settlement. Faster settlement makes evidence-led checks
before the trigger more valuable.”

## Round 2 — one minute

Trade-finance fraud in GIFT City is hard to see when each IBU validates in
isolation. TradeSentry is an AI-assisted pre-settlement intelligence layer: AWS
Textract extracts facts, deterministic Python evaluates reviewed UCP 600 rules,
and a constrained agent queries a DynamoDB Transaction DNA registry and selects
approved TBML checks. Clean and legitimate repeat trades produce no alert;
duplicate B/L and significant price signals stop at a human-review gate. The
staging architecture runs on AWS services funded by hackathon credits, with
measured health and a complete audit trail. Humans authorize every consequential
decision. We sit upstream of FCSS—because faster settlement makes intelligence
before the trigger more valuable.

## Never say

- autonomous LC safety decision
- every alert is fraud
- real IBU data
- we control or integrate with FCSS
- prototype thresholds are regulatory standards
- AI replaces the compliance officer
- a hard-coded DynamoDB latency; quote the measured timeline value
