"""Inter-agent guardrails: prerequisite checks and cross-agent state consistency."""
from typing import Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from state.trip_state import TripState

# ── Required state fields before each agent runs ─────────────────
AGENT_PREREQUISITES: dict = {
    "memory_retrieval_agent": ["user_query", "trip_preferences"],
    "weather_agent":          ["trip_preferences"],
    "transport_agent":        ["trip_preferences"],
    "hotel_agent":            ["trip_preferences"],
    "places_agent":           ["trip_preferences"],
    "budget_agent":           ["trip_preferences", "transport_data", "hotel_data"],
    "itinerary_agent":        ["trip_preferences", "weather_data", "transport_data",
                               "hotel_data", "places_data", "budget_summary"],
    "review_agent":           ["trip_preferences", "itinerary", "budget_summary"],
    "orchestrator_validate":  ["review_status"],
    "memory_update_agent":    ["trip_preferences", "itinerary", "budget_summary"],
    "pdf_generator_agent":    ["trip_preferences"],
}

# ── Max acceptable retry count before we flag a loop ─────────────
MAX_SAFE_RETRY = 5
KNOWN_STATUSES = {"running", "approved", "failed", "done", "error", "blocked", ""}


def validate_state_before_agent(agent_name: str, state: dict) -> Tuple[bool, List[str]]:
    """
    Verify all required state fields exist and are non-empty before an agent runs.
    Returns (is_ready, list_of_missing_fields).
    """
    required = AGENT_PREREQUISITES.get(agent_name, [])
    missing = [f for f in required if not state.get(f)]
    return len(missing) == 0, missing


def check_inter_agent_consistency(state: dict) -> List[str]:
    """
    Cross-validate that agent outputs agree with each other and with user preferences.
    Returns list of inconsistency descriptions.
    """
    issues = []
    prefs = state.get("trip_preferences") or {}
    destination = str(prefs.get("destination", "")).lower().strip()
    budget = prefs.get("budget", 0)

    # Hotel location must match destination
    hotel_data = state.get("hotel_data") or {}
    if hotel_data and not hotel_data.get("error"):
        hotels = hotel_data.get("hotels", [])
        if hotels and destination:
            top = hotels[0]
            loc = str(top.get("location", top.get("city", ""))).lower()
            if loc and destination not in loc and loc not in destination:
                issues.append(
                    f"Hotel location mismatch: destination='{destination}', "
                    f"top hotel location='{loc}'"
                )

    # Transport destination must match
    transport_data = state.get("transport_data") or {}
    if transport_data and not transport_data.get("error"):
        flights = transport_data.get("flights", [])
        if flights and destination:
            for flight in flights[:2]:
                arr = str(flight.get("arrival_city", flight.get("to", ""))).lower()
                if arr and destination not in arr and arr not in destination:
                    issues.append(
                        f"Flight destination mismatch: expected '{destination}', "
                        f"got arrival '{arr}'"
                    )
                    break

    # Budget summary total_budget must match trip preferences budget (within 10%)
    budget_summary = state.get("budget_summary") or {}
    if budget_summary and budget:
        summary_budget = budget_summary.get("total_budget", 0)
        try:
            if float(summary_budget) > 0:
                diff_pct = abs(float(summary_budget) - float(budget)) / float(budget)
                if diff_pct > 0.10:
                    issues.append(
                        f"Budget mismatch: trip_preferences.budget=₹{budget:,}, "
                        f"budget_summary.total_budget=₹{summary_budget:,} "
                        f"({diff_pct*100:.0f}% divergence)"
                    )
        except (TypeError, ValueError):
            pass

    # Itinerary day count should match num_days preference
    itinerary = state.get("itinerary") or {}
    if itinerary:
        itin_days = len(itinerary.get("days", []))
        pref_days = int(prefs.get("num_days") or 0)
        if pref_days > 0 and itin_days > 0 and abs(itin_days - pref_days) > 1:
            issues.append(
                f"Itinerary day count mismatch: requested {pref_days} days, "
                f"itinerary has {itin_days} days"
            )

    # Retry loop detection
    retry_count = state.get("retry_count", 0)
    if retry_count > MAX_SAFE_RETRY:
        issues.append(
            f"High retry count ({retry_count}) — possible infinite loop in workflow"
        )

    return issues


def check_state_field_integrity(state: dict) -> List[str]:
    """
    Check for structurally corrupted state values.
    Returns list of integrity violations.
    """
    violations = []

    if "messages" in state and not isinstance(state["messages"], list):
        violations.append(f"'messages' is not a list: {type(state['messages']).__name__}")

    if "error_log" in state and not isinstance(state["error_log"], list):
        violations.append(f"'error_log' is not a list: {type(state['error_log']).__name__}")

    if "guardrail_log" in state and not isinstance(state["guardrail_log"], list):
        violations.append(f"'guardrail_log' is not a list: {type(state['guardrail_log']).__name__}")

    retry = state.get("retry_count", 0)
    if not isinstance(retry, int) or retry < 0:
        violations.append(f"Invalid retry_count: {retry!r}")

    status = state.get("status", "")
    if status and status not in KNOWN_STATUSES:
        violations.append(f"Unknown status value: '{status}'")

    return violations
