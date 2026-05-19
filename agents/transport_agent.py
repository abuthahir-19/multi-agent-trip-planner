"""Transport Agent — finds best flights, trains, and routes."""
from tools.transport_tool import search_transport
from state.trip_state import TripState


def transport_agent(state: TripState) -> dict:
    """Search and recommend transport options for the trip."""
    prefs = state.get("trip_preferences", {})
    budget = float(prefs.get("budget", 30000))
    num_travelers = int(prefs.get("num_travelers", 2))
    budget_per_person = budget / num_travelers

    try:
        transport_data = search_transport(
            source=prefs.get("source", ""),
            destination=prefs.get("destination", ""),
            travel_dates=prefs.get("travel_dates", ""),
            num_travelers=num_travelers,
            transport_preference=prefs.get("transport_preference", "any"),
            budget_per_person=budget_per_person,
        )
        return {
            "transport_data": transport_data,
            "messages": [{"role": "system", "content":
                          f"Transport Agent: Found options. Recommended: {transport_data.get('recommended', 'N/A')}"}],
        }
    except Exception as e:
        return {
            "transport_data": {"error": str(e)},
            "error_log": [f"Transport Agent error: {e}"],
            "messages": [{"role": "system", "content": f"Transport Agent: Error — {e}"}],
        }
