# rules/agent_constraints.py

TOOL_ALLOW_LIST = {
    "price_benchmark",
    "verify_vessel",
    "verify_entity",
    "screen_sanctions",
}

MAX_TOOL_CALLS_PER_CASE = 12
TOOL_TIMEOUT_SECONDS    = 30

def validate_tool_selection_plan(plan: dict) -> tuple[bool, list[str]]:
    errors = []

    requested_tools = [
        k for k, v in plan.items()
        if k.startswith("run_") and v is True
    ]

    for tool_key in requested_tools:
        tool_name = tool_key.replace("run_", "")
        if tool_name not in TOOL_ALLOW_LIST:
            errors.append(
                f"Tool '{tool_name}' not in approved allow-list. "
                f"Approved: {TOOL_ALLOW_LIST}"
            )

    if not plan.get("reasoning"):
        errors.append("ToolSelectionPlan.reasoning is required and cannot be empty")

    return (len(errors) == 0, errors)
