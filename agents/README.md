# Agents

Sprint 6 uses LangGraph to coordinate deterministic service calls and four
allow-listed, read-only fraud/TBML tools. The planner receives only a validated
`TriageContext`; raw document text is never included in planner input.

The graph cannot evaluate UCP rules, mutate persistence directly, call an
arbitrary function, or perform settlement. High-risk, material-compliance, and
exact cross-IBU outcomes pause at a human-review interrupt. Any readiness value
is an advisory for a downstream bank workflow, not a settlement action.
