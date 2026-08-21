# ADR 0001: AWS-first foundation

## Status

Accepted for the hackathon prototype.

## Decision

Use FastAPI and Next.js in separate ECS-compatible containers. PostgreSQL is the durable relational store, Redis is transient cache, and S3 stores immutable document objects. Local development uses equivalent containers and in-memory test doubles. AWS credentials are resolved from workload roles or temporary local profiles and are never embedded in code.

## Consequences

Sprint 0 proves interfaces and deployability without claiming live service availability. Later sprints may implement the interfaces but must retain human authorization and evidence provenance.
