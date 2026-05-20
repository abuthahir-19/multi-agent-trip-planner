"""LangGraph-compatible guardrail node functions.

Two nodes are inserted into the workflow:
  input_guardrail_node  — after user_input_agent, before memory_retrieval_agent
  output_guardrail_node — after review_agent, before orchestrator_validate
"""
from guardrails.input_guard import validate_user_query, sanitize_text, validate_trip_preferences
from guardrails.output_guard import (
    validate_agent_output, validate_budget_output,
    validate_itinerary_output,
)
from guardrails.agent_guard import check_inter_agent_consistency, check_state_field_integrity


def input_guardrail_node(state: dict) -> dict:
    """
    Input security layer — runs immediately after user_input_agent.

    Checks:
      1. Prompt injection / attack patterns in raw query
      2. PII in raw query (advisory)
      3. Extracted trip preferences schema & value bounds
      4. Auto-fixes trivial issues (zero budget, zero days)
    """
    log: list = []
    updates: dict = {}

    query = state.get("user_query", "")

    # 1. Validate and sanitize raw query
    is_safe, violations = validate_user_query(query)
    for v in violations:
        log.append(f"[INPUT] {v}")

    sanitized = sanitize_text(query)
    if sanitized != query:
        updates["user_query"] = sanitized
        log.append("[INPUT][SANITIZED] Query was cleaned (HTML/template patterns removed)")

    # 2. Validate extracted trip preferences
    prefs = state.get("trip_preferences") or {}
    if prefs:
        _, pref_issues = validate_trip_preferences(prefs)
        for issue in pref_issues:
            log.append(f"[PREFS] {issue}")

        # Auto-fix trivially wrong values so downstream agents aren't broken
        fixed = dict(prefs)
        changed = False
        if not fixed.get("budget") or float(fixed.get("budget", 0)) <= 0:
            fixed["budget"] = 30000
            log.append("[PREFS][AUTO-FIX] Budget defaulted to ₹30,000")
            changed = True
        if not fixed.get("num_days") or int(fixed.get("num_days", 0)) <= 0:
            fixed["num_days"] = 5
            log.append("[PREFS][AUTO-FIX] num_days defaulted to 5")
            changed = True
        if not fixed.get("num_travelers") or int(fixed.get("num_travelers", 0)) <= 0:
            fixed["num_travelers"] = 1
            log.append("[PREFS][AUTO-FIX] num_travelers defaulted to 1")
            changed = True
        if changed:
            updates["trip_preferences"] = fixed

    # 3. Build return dict
    result: dict = {
        "guardrail_log": log,
        "messages": [{
            "role": "guardrail",
            "content": (
                f"Input Guardrail: {len(log)} flag(s) — "
                + ("BLOCKED unsafe input" if not is_safe else "passed")
            ),
        }],
    }

    if not is_safe:
        result["status"] = "blocked"
        result["error_log"] = [
            f"[GUARDRAIL BLOCK] Unsafe input rejected: {'; '.join(v for v in log if '[INPUT] Security' in v)}"
        ]

    result.update(updates)
    return result


def output_guardrail_node(state: dict) -> dict:
    """
    Output security & quality layer — runs after review_agent, before orchestrator_validate.

    Checks:
      1. State field integrity (types, known values)
      2. Cross-agent consistency (destination, budget, day-count alignment)
      3. Budget output sanity (price bounds, 10x overflow detection)
      4. Itinerary output completeness
      5. Review output schema
    """
    log: list = []

    # 1. State integrity
    for issue in check_state_field_integrity(state):
        log.append(f"[INTEGRITY] {issue}")

    # 2. Cross-agent consistency
    for issue in check_inter_agent_consistency(state):
        log.append(f"[CONSISTENCY] {issue}")

    # 3. Budget sanity
    budget = state.get("budget_summary") or {}
    if budget:
        _, issues = validate_budget_output(budget)
        for issue in issues:
            log.append(f"[BUDGET] {issue}")

    # 4. Itinerary completeness
    itinerary = state.get("itinerary") or {}
    if itinerary:
        _, issues = validate_itinerary_output(itinerary)
        for issue in issues:
            log.append(f"[ITINERARY] {issue}")

    # 5. Review schema
    review = state.get("review_status") or {}
    if review:
        _, issues = validate_agent_output("review_agent", review)
        for issue in issues:
            log.append(f"[REVIEW] {issue}")

    summary = f"Output Guardrail: {len(log)} issue(s) found" if log else "Output Guardrail: All checks passed"
    result: dict = {
        "guardrail_log": log,
        "messages": [{"role": "guardrail", "content": summary}],
    }
    if log:
        result["error_log"] = log

    return result
