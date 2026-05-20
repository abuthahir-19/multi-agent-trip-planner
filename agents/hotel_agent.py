"""Hotel Agent — finds accommodations within budget."""
from tools.hotel_tool import search_hotels
from state.trip_state import TripState


def hotel_agent(state: TripState) -> dict:
    """Search hotels that match the user's budget and preferences."""
    prefs = state.get("trip_preferences", {})
    budget = float(prefs.get("budget", 30000))
    num_days = int(prefs.get("num_days", 5))
    num_travelers = int(prefs.get("num_travelers", 2))

    # Allocate ~30% of budget to hotel (₹ per night)
    hotel_budget_per_night = (budget * 0.30) / num_days

    try:
        hotel_data = search_hotels(
            destination=prefs.get("destination", ""),
            check_in=prefs.get("travel_dates", "").split(" to ")[0] if " to " in str(prefs.get("travel_dates", "")) else str(prefs.get("travel_dates", "")),
            check_out=prefs.get("travel_dates", "").split(" to ")[-1] if " to " in str(prefs.get("travel_dates", "")) else "",
            num_travelers=num_travelers,
            budget_per_night=hotel_budget_per_night,
            hotel_preference=prefs.get("hotel_preference", "3-star"),
            trip_type=prefs.get("trip_type", "couple"),
        )
        recommended = hotel_data.get("recommended", {})
        return {
            "hotel_data": hotel_data,
            "messages": [{"role": "system", "content":
                          f"Hotel Agent: Recommended '{recommended.get('name', 'N/A')}' "
                          f"at ₹{recommended.get('price_per_night', 0):,}/night"}],
        }
    except Exception as e:
        return {
            "hotel_data": {"error": str(e)},
            "error_log": [f"Hotel Agent error: {e}"],
            "messages": [{"role": "system", "content": f"Hotel Agent: Error — {e}"}],
        }
