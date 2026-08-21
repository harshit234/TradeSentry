# Trade Finance Intelligence Layer

AWS-first, human-authorized pre-settlement intelligence prototype for simulated GIFT City IBU workflows.

## Current scope: Sprint 4

The foundation now includes document intelligence, deterministic compliance, Transaction DNA, and Sprint 4 simulated cross-IBU intelligence. The permissioned DynamoDB registry stores normalized signal fields only, uses three GSIs and a 90-day TTL, and preserves tenant isolation and append-only audits.

Investigation agents, fraud decisions, and settlement actions remain intentionally absent until their own sprints. Cross-IBU matches are prototype investigation signals—not proof of duplicate financing, legal identity, wrongdoing, or fraud—and humans remain the final authority.

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

Bedrock fallback is optional. Set `BEDROCK_MODEL_ID` and use an AWS profile locally or the ECS task role in AWS; never store a Bedrock credential in this repository.

Run backend tests with `pytest` and the frontend checks with `npm --prefix apps/web run build`.
