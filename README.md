# Trade Finance Intelligence Layer

AWS-first, human-authorized pre-settlement intelligence prototype for simulated GIFT City IBU workflows.

## Current scope: Sprint 1

The Sprint 0 foundation now includes Sprint 1 document intelligence: secure document upload, classification for seven trade-document types, Textract orchestration, typed extraction evidence, confidence and page references, completeness gating, durable persistence, and an idempotent 28-document demo seed.

Compliance rules, cross-IBU intelligence, investigation agents, fraud decisions, and settlement actions remain intentionally absent until their own sprints. Risk signals are not legal findings, and humans remain the final authority.

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

Bedrock fallback is optional. Set `BEDROCK_MODEL_ID` and use an AWS profile locally or the ECS task role in AWS; never store a Bedrock credential in this repository.

Run backend tests with `pytest` and the frontend checks with `npm --prefix apps/web run build`.
