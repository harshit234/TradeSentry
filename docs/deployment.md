# AWS staging deployment

## AWS Credits

Deployed on AWS using credits provided at the AWS Tools & Credits Briefing
(Friday 21 Aug 2026) as part of the hackathon.

Services:

- AWS Textract — OCR and structured extraction using AnalyzeDocument with forms, tables, and queries.
- ECS/Fargate — containerized API and dashboard runtime.
- RDS PostgreSQL — persistent case, compliance, investigation, decision, and audit data.
- ElastiCache Redis — TLS-protected session and rate-limit cache.
- DynamoDB — cross-IBU intelligence registry (`TradeFinanceRegistry` plus three GSIs).
- S3 — immutable document storage with KMS encryption and versioning.
- ECR — KMS-encrypted, scan-on-push API and web image repositories.
- Secrets Manager — runtime database, Redis, and JWT configuration; no repository secrets.
- KMS — envelope encryption for S3, RDS, DynamoDB, ECR, Secrets Manager, and logs.
- CloudWatch — structured ECS logs, metrics, Container Insights, and alarms.

All services are in `ap-south-1`. No document data leaves the AWS boundary.
Estimated credit consumption for a 12-hour live demo window is USD 3–6; verify
the actual amount in AWS Cost Explorer before submission.

## Architecture and security

The public Application Load Balancer routes the dashboard by default and API
paths to a separate target group. Only the ALB can reach ECS ports. RDS and
Redis accept traffic only from the ECS security group. RDS is not public,
Redis requires TLS, S3 is private/versioned/KMS-only, and DynamoDB uses a KMS
key, point-in-time recovery, TTL, and three GSIs. ECS receives only the public
JWT verification key; the demo signing key remains in Secrets Manager and is
never available to the application task role.

## Commands

Prerequisites: AWS CLI login profile `tradesentry-dev`, Docker Desktop,
Terraform 1.7+, GNU Make, and the project virtual environment.

```powershell
make deploy-staging
make health-check
make seed-demo
make demo-token IBU_ID=IBU-A
make rollback-staging
```

`deploy-staging` is intentionally two phase. Terraform first creates the data
plane with ECS desired count zero. The script then pushes git-SHA and `latest`
image tags, writes generated runtime credentials directly to encrypted Secrets
Manager, and starts one API and one web task. No credential is written to disk.

`rollback-staging` selects the immediately preceding active task definition for
both services, waits for stability, and re-runs the health gate. It fails closed
when a previous revision is unavailable.

Terraform retains earlier ECS task-definition revisions so rollback targets an
immutable image that was deployed previously. The API task uses 1 vCPU and 2 GB
memory to keep the live DynamoDB demonstration path responsive.

## Verification

The release gate requires `/health` to report `ok` for PostgreSQL, Redis, S3,
Textract, and DynamoDB, with the deployed git SHA. Then run `make seed-demo` and
verify all four cases against [the demo runbook](demo-runbook.md). Seeded demo
documents use reviewed deterministic extraction fixtures for presentation
stability; the normal upload path uses live AWS Textract. This distinction must
remain explicit during judging.
