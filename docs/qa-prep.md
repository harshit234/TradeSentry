# Jury Q&A preparation

## 1. What makes this agentic?

A fixed pipeline would call every tool. Our constrained LangGraph workflow reads
structured state and selects only approved, read-only investigation tools. A
clean case uses at most four calls; suspicious cases use more. Selection reasons,
hashed inputs, status, and measured latency are visible in the timeline.

## 2. How do you stop hallucinated compliance rules?

The LLM never evaluates UCP rules. The deterministic Python engine accepts only
versioned rule IDs. Sprint 9 Case M injects a fabricated ID and proves the engine
rejects it. Every real finding retains rule ID, article, expected, actual, and
evidence provenance.

## 3. Why DynamoDB?

The normalized fingerprint registry is read-heavy and latency-sensitive.
DynamoDB provides exact B/L, vessel/date, and exporter GSIs, TTL expiry,
point-in-time recovery, KMS encryption, and IAM-scoped access. We show measured
query latency rather than promising a universal sub-5ms result.

## 4. Does cross-IBU sharing expose customer data?

No raw documents or customer records enter the registry. It stores an approved
normalized signal set and an entity hash. Production use would still require
permissioned data-sharing agreements, governance, and regulatory approval. The
MVP contains synthetic data only.

## 5. Who chose the price threshold?

We did, as a prototype value clearly labelled as such. The result is a review
signal with its reference range, source, deviation, and caveats—not proof of
fraud. Production calibration requires historical analysis and compliance and
risk sign-off.

## 6. What did AWS credits enable?

They fund the staging data plane and runtime: Textract, ECS, RDS, DynamoDB,
ElastiCache, S3, ECR, Secrets Manager, KMS, and CloudWatch. `/health`, ECS task
state, CloudWatch logs, and the deployment report are the evidence. Do not claim
a service is live unless it is verified during pre-flight.

## 7. Is this FCSS integration?

No. FCSS is downstream settlement infrastructure. TradeSentry provides an
informational readiness state before the bank's settlement workflow; it does
not control, call, execute, or simulate FCSS settlement.
