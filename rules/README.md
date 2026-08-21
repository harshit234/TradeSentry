# Deterministic compliance rules

This package implements only the Sprint 2 checks supplied by the project specification. It has no FastAPI, database, network, or LLM dependency.

- `config/ucp600_rules.json` contains enabled definitions, versions, and prototype thresholds.
- `parser.py` maps typed Sprint 1 LC extraction fields without inferring facts.
- `checks.py` contains isolated article-referenced functions.
- `engine.py` executes completeness first, stops on incomplete presentations, orders findings deterministically, and returns stable finding IDs.

Rule evaluation never calls Bedrock or Textract. Every finding carries its configured rule ID, UCP article, expected and actual values, evidence provenance, page reference, severity, and rule version. All consequential decisions remain with a human officer.
