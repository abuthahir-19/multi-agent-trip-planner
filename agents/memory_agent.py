"""Memory Agent — retrieves and updates user travel preferences from vector store."""
from memory.vector_store import retrieve_user_preferences, search_similar_trips
from state.trip_state import TripState


def memory_retrieval_agent(state: TripState) -> dict:
    """Retrieve past preferences and similar trips for the current user."""
    user_profile = state.get("user_profile", {})
    user_id = user_profile.get("user_id", "default_user")
    prefs = state.get("trip_preferences", {})
    destination = prefs.get("destination", "")

    past_prefs = retrieve_user_preferences(user_id)
    similar_trips = search_similar_trips(
        destination=destination,
        preferences=str(prefs.get("places_of_interest", "")),
        n_results=3
    )

    memory_context = {
        "past_preferences": past_prefs,
        "similar_trips": similar_trips,
        "personalization_notes": _build_personalization(past_prefs, prefs),
    }

    # Enrich current preferences with remembered defaults
    enriched_prefs = dict(prefs)
    if past_prefs and not prefs.get("food_preference"):
        enriched_prefs["food_preference"] = past_prefs.get("food_preference", "any")
    if past_prefs and not prefs.get("hotel_preference"):
        enriched_prefs["hotel_preference"] = past_prefs.get("hotel_preference", "3-star")

    return {
        "memory_context": memory_context,
        "trip_preferences": enriched_prefs,
        "messages": [{"role": "system", "content":
                      f"Memory Agent: Retrieved {len(similar_trips)} similar trips for user {user_id}"}],
    }


def memory_update_agent(state: TripState) -> dict:
    """Save the completed trip to memory after a successful plan."""
    from memory.vector_store import store_user_preferences, store_trip_history
    user_profile = state.get("user_profile", {})
    user_id = user_profile.get("user_id", "default_user")
    prefs = state.get("trip_preferences", {})
    budget = state.get("budget_summary", {})

    store_user_preferences(user_id, {
        "hotel_preference": prefs.get("hotel_preference", ""),
        "food_preference": prefs.get("food_preference", ""),
        "transport_preference": prefs.get("transport_preference", ""),
        "trip_type": prefs.get("trip_type", ""),
        "luxury_vs_budget": prefs.get("luxury_vs_budget", ""),
    })

    store_trip_history(user_id, {
        "destination": prefs.get("destination", ""),
        "source": prefs.get("source", ""),
        "dates": prefs.get("travel_dates", ""),
        "budget": budget.get("total_estimated", 0),
        "trip_type": prefs.get("trip_type", ""),
        "num_days": prefs.get("num_days", 0),
    })

    return {
        "messages": [{"role": "system", "content": "Memory Agent: Preferences and trip history saved."}],
    }


def _build_personalization(past_prefs: dict, current_prefs: dict) -> str:
    if not past_prefs:
        return "No previous trips found. Starting fresh."
    notes = []
    if past_prefs.get("food_preference"):
        notes.append(f"Prefers {past_prefs['food_preference']} food")
    if past_prefs.get("hotel_preference"):
        notes.append(f"Usually books {past_prefs['hotel_preference']} hotels")
    if past_prefs.get("transport_preference"):
        notes.append(f"Preferred transport: {past_prefs['transport_preference']}")
    return "; ".join(notes) if notes else "Returning user with no specific past preferences."
