# TradeSentry threat model

## Scope and trust boundaries

TradeSentry is an investigation and human-review system for synthetic trade-finance workflows. It does not execute settlement and does not control FCSS. The protected assets are trade documents in S3, extracted fields and officer decisions in PostgreSQL, privacy-preserving cross-IBU signals in DynamoDB, the append-only audit trail, and application credentials in Secrets Manager.

The primary boundaries are the browser-to-API RS256 token boundary, ECS-to-private-data-service network boundary, IBU tenant boundary, document-to-extraction boundary, and structured-evidence-to-agent boundary.

## Threats and controls

### 1. Unauthorized cross-IBU access

An officer could alter a case ID, request header, or DynamoDB key to access another IBU's data.

Controls: the API derives `ibu_id` only from the verified JWT; every case lookup verifies the stored IBU; DynamoDB partition keys use `IBU#{ibu_id}`; officers cannot call cross-IBU routes; compliance managers receive matching signals rather than foreign raw cases; DynamoDB's resource policy denies access outside the ECS task role.

### 2. Malicious document upload

An attacker could disguise an executable as a PDF, exploit a malformed document, or upload malware.

Controls: the service reads only the configured maximum size, detects MIME type from magic bytes, parses PDF structure before storage, uses BucketOwnerEnforced S3 objects, and invokes a malware-scanner interface. The deterministic local scanner detects the EICAR test signature. The production ClamAV adapter remains fail-closed until implemented.

### 3. Prompt injection through documents

Document text could contain instructions intended to redirect an LLM or invoke an unapproved tool.

Controls: agents receive typed structured fields rather than raw text; compliance rules remain deterministic Python; planner output is schema-validated; tool execution is restricted to the existing allow-list and budget; unknown rule identifiers and tool names are rejected.

### 4. Agent bypass of human review

An agent recommendation could be mistaken for authorization to proceed.

Controls: the settlement-readiness gate is deterministic Python; every case remains `HOLD — AWAITING OFFICER` until an authenticated OFFICER records approval; idempotent officer decisions are immutable; TradeSentry has no settlement execution tool.

### 5. Replay or impersonation of an officer decision

An attacker could replay a decision request or use a refresh token as an access token.

Controls: only RS256 access tokens are accepted; issuer, audience, signature, expiry, issue time, role, officer ID and IBU are verified; access lifetime is capped at one hour; refresh tokens are rejected by protected endpoints; a 16-character minimum idempotency key is hashed and uniquely bound to each case.

### 6. Audit or credential compromise

An operator could alter audit rows, or secrets and signed URLs could leak through logs.

Controls: audit rows are insert-only with a PostgreSQL mutation-blocking trigger; all 18 event types use opaque references; comments are represented by hashes; IP addresses are hashed; JSON logging redacts bearer tokens, JWTs, secrets and signed URLs; S3, RDS, DynamoDB, ECR and Secrets Manager use encryption; IAM permissions are resource-scoped wherever AWS supports it.

## AWS IAM exceptions

AWS does not support resource-level permissions for Textract, `ecr:GetAuthorizationToken`, or `ecs:RegisterTaskDefinition`. Those three statements require `Resource = "*"`; their action lists are exact and isolated from all resource-scoped permissions. No wildcard action is granted. DynamoDB GSI permissions enumerate each named index.

## Remaining MVP risks

- The ClamAV network integration is a fail-closed stub rather than a production scanner.
- The application does not independently require an MFA authentication-method claim, although the upstream identity provider can enforce MFA.
- Deployment is single-region.
- Sanctions data is not a real-time production feed.
- In-memory rate limiting is process-local in test mode; live deployments use Redis.
- OpenTelemetry export still depends on the configured private collector's availability.

## Validation cadence

Run the security acceptance suite and Terraform validation on every change. Review IAM policy diffs, dependency scans, audit event coverage, cross-IBU denial tests and log-redaction tests before deployment. Prototype risk thresholds remain investigation signals, not regulatory standards or proof of fraud.
