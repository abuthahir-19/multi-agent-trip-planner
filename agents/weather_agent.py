"""Weather Agent — fetches and interprets weather for travel dates."""
from tools.weather_tool import get_weather_forecast
from state.trip_state import TripState


def weather_agent(state: TripState) -> dict:
    """Fetch weather forecast for the destination."""
    prefs = state.get("trip_preferences", {})
    destination = prefs.get("destination", "")
    travel_dates = prefs.get("travel_dates", "")

    if not destination:
        return {
            "weather_data": {"error": "No destination specified"},
            "error_log": ["Weather Agent: No destination provided"],
            "messages": [{"role": "system", "content": "Weather Agent: Skipped — no destination"}],
        }

    try:
        weather_data = get_weather_forecast(destination, travel_dates)
        return {
            "weather_data": weather_data,
            "messages": [{"role": "system", "content":
                          f"Weather Agent: Fetched forecast for {destination}. "
                          f"Summary: {weather_data.get('summary', 'N/A')}"}],
        }
    except Exception as e:
        return {
            "weather_data": {"error": str(e), "city": destination},
            "error_log": [f"Weather Agent error: {e}"],
            "messages": [{"role": "system", "content": f"Weather Agent: Error — {e}"}],
        }
