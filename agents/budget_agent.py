"""Budget Agent — estimates trip cost and suggests optimizations."""
from tools.budget_tool import calculate_budget
from state.trip_state import TripState


def budget_agent(state: TripState) -> dict:
    """Calculate total trip cost and optimize within budget."""
    prefs = state.get("trip_preferences", {})
    transport_data = state.get("transport_data", {})
    hotel_data = state.get("hotel_data", {})

    try:
        budget_summary = calculate_budget(
            trip_preferences=prefs,
            transport_data=transport_data,
            hotel_data=hotel_data,
        )

        over = budget_summary.get("over_budget", False)
        total = budget_summary.get("total_estimated", 0)
        limit = budget_summary.get("total_budget", 0)

        msg = (
            f"Budget Agent: Estimated ₹{total:,} vs budget ₹{limit:,}. "
            f"{'OVER BUDGET — optimization needed.' if over else 'Within budget.'}"
        )

        return {
            "budget_summary": budget_summary,
            "messages": [{"role": "system", "content": msg}],
        }
    except Exception as e:
        return {
            "budget_summary": {"error": str(e)},
            "error_log": [f"Budget Agent error: {e}"],
            "messages": [{"role": "system", "content": f"Budget Agent: Error — {e}"}],
        }
