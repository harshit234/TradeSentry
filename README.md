# Trade Finance Intelligence Layer

AWS-first, human-authorized pre-settlement intelligence prototype for simulated GIFT City IBU workflows.

## Current scope: Sprint 5

The foundation now includes document intelligence, deterministic compliance,
Transaction DNA, simulated cross-IBU intelligence, and four read-only Sprint 5
fraud/TBML investigation tools: price benchmarking, vessel verification,
entity verification, and sanctions screening.

The tool runner enforces configurable timeouts, retries only idempotent reads,
returns typed results with provenance and caveats, and appends audit events for
every invocation. Its bundled data is synthetic/static demo data. Signals are
not proof of fraud, fuzzy sanctions matches are never auto-confirmed, and a
human officer remains the final authority. Agent orchestration, fraud decisions,
and settlement actions remain intentionally absent until their own sprints.

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
- `POST /cross-ibu/register` (`X-IBU-ID` required)
- `POST /cross-ibu/query` (`X-IBU-ID` required)
- `GET /cross-ibu/registry` (`X-Admin-Debug: true`, simulated admin/debug only)

Transaction DNA uses only deterministic, bundled normalization data. Unknown currencies are left unconverted rather than applying a guessed exchange rate.

All cross-IBU weights and thresholds are configurable prototype demo values, not regulatory standards. The synthetic registry can be loaded with `make seed-registry`; it contains no real IBU or customer data.

Sprint 5 tool thresholds are also prototype demo values, not regulatory
standards. Production provider classes are non-operational stubs; the MVP makes
no live price, AIS, entity-intelligence, or sanctions API calls at runtime.

Bedrock fallback is optional. Set `BEDROCK_MODEL_ID` and use an AWS profile locally or the ECS task role in AWS; never store a Bedrock credential in this repository.

Run backend tests with `pytest` and the frontend checks with `npm --prefix apps/web run build`.
