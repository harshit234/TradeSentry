# Trade Finance Intelligence Layer

AWS-first, human-authorized pre-settlement intelligence prototype for simulated GIFT City IBU workflows.

## Current scope: Sprint 3

The Sprint 0 foundation now includes Sprint 1 document intelligence, Sprint 2 deterministic compliance, and Sprint 3 Transaction DNA: secure document upload, typed extraction evidence, completeness gating, a versioned pure-Python UCP rule engine, deterministic multi-document normalization, field provenance, preserved conflicts, confidence flags, and a stable SHA-256 trade fingerprint.

Cross-IBU duplicate detection, investigation agents, fraud decisions, and settlement actions remain intentionally absent until their own sprints. Transaction DNA is an evidence artifact, not proof of legal identity or wrongdoing, and humans remain the final authority.

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

Transaction DNA uses only deterministic, bundled normalization data. Unknown currencies are left unconverted rather than applying a guessed exchange rate.

Bedrock fallback is optional. Set `BEDROCK_MODEL_ID` and use an AWS profile locally or the ECS task role in AWS; never store a Bedrock credential in this repository.

Run backend tests with `pytest` and the frontend checks with `npm --prefix apps/web run build`.
