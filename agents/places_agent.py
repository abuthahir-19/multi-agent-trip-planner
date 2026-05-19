"""Places Explorer Agent — discovers tourist attractions and local experiences."""
from tools.places_tool import explore_places
from state.trip_state import TripState


def places_agent(state: TripState) -> dict:
    """Explore tourist attractions, food, and local experiences."""
    prefs = state.get("trip_preferences", {})
    weather = state.get("weather_data", {})

    weather_condition = weather.get("travel_advisory", "") or weather.get("summary", "")

    try:
        places_data = explore_places(
            destination=prefs.get("destination", ""),
            places_of_interest=prefs.get("places_of_interest", []),
            trip_type=prefs.get("trip_type", "couple"),
            food_preferences=prefs.get("food_preference", "any"),
            weather_condition=weather_condition,
        )
        n_attractions = len(places_data.get("top_attractions", []))
        return {
            "places_data": places_data,
            "messages": [{"role": "system", "content":
                          f"Places Agent: Found {n_attractions} attractions and local experiences."}],
        }
    except Exception as e:
        return {
            "places_data": {"error": str(e)},
            "error_log": [f"Places Agent error: {e}"],
            "messages": [{"role": "system", "content": f"Places Agent: Error — {e}"}],
        }
