# Trade Finance Intelligence Layer

AWS-first, human-authorized pre-settlement intelligence prototype for simulated GIFT City IBU workflows.

## Current scope: Sprint 10

The platform now includes document intelligence, deterministic compliance,
Transaction DNA, simulated cross-IBU intelligence, four read-only Sprint 5
fraud/TBML investigation tools: price benchmarking, vessel verification,
entity verification, and sanctions screening, plus a constrained LangGraph
investigation workflow.

The tool runner enforces configurable timeouts, retries only idempotent reads,
returns typed results with provenance and caveats, and appends audit events for
every invocation. Its bundled data is synthetic/static demo data. Signals are
not proof of fraud, fuzzy sanctions matches are never auto-confirmed, and a
human officer remains the final authority. The workflow uses deterministic
compliance and risk services, a structured triage plan, a 12-call default
budget, hashed tool telemetry, and mandatory human-review interrupts. It does
not make fraud findings or settlement decisions.

## Local development

```bash
cp .env.example .env
docker compose -f infra/docker/docker-compose.yml up --build
```

- API: http://localhost:8000/health
- Web: http://localhost:3000

Seed the four synthetic demo cases after the stack is healthy:

```bash
make seed-demo
```

Document endpoints:

- `POST /cases`
- `POST /cases/{case_id}/documents`
- `GET /cases/{case_id}/documents`
- `GET /cases/{case_id}/documents/{document_id}`
- `GET /cases/{case_id}/completeness`
- `POST /cases/{case_id}/compliance`
- `GET /cases/{case_id}/compliance`
- `POST /cases/{case_id}/transaction-dna`
- `GET /cases/{case_id}/transaction-dna`
- `POST /cases/{case_id}/run` (`X-IBU-ID` required)
- `GET /cases/{case_id}/investigation` (`X-IBU-ID` required)
- `POST /cross-ibu/register` (`X-IBU-ID` required)
- `POST /cross-ibu/query` (`X-IBU-ID` required)
- `GET /cross-ibu/registry` (`X-Admin-Debug: true`, simulated admin/debug only)

Transaction DNA uses only deterministic, bundled normalization data. Unknown currencies are left unconverted rather than applying a guessed exchange rate.

All cross-IBU weights and thresholds are configurable prototype demo values, not regulatory standards. The synthetic registry can be loaded with `make seed-registry`; it contains no real IBU or customer data.

Sprint 5 tool thresholds are also prototype demo values, not regulatory
standards. Production provider classes are non-operational stubs; the MVP makes
no live price, AIS, entity-intelligence, or sanctions API calls at runtime.

All risk weights and the USD 700 triage threshold are prototype demo values,
not calibrated production or regulatory standards. A `READY FOR BANK SETTLEMENT
WORKFLOW` result is informational only: no settlement tool exists in the agent
allow-list and no settlement is executed or simulated.

Bedrock fallback is optional. Set `BEDROCK_MODEL_ID` and use an AWS profile locally or the ECS task role in AWS; never store a Bedrock credential in this repository.

Run backend tests with `pytest` and the frontend checks with `npm --prefix apps/web run build`.

Sprint 10 AWS deployment and presentation instructions are in
[`docs/deployment.md`](docs/deployment.md) and
[`docs/demo-runbook.md`](docs/demo-runbook.md). The repository never treats a
Terraform plan as proof of a live deployment; use the staging health gate and
CloudWatch/ECS checks before making live-infrastructure claims.
