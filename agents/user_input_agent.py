"""User Input Agent — collects and validates trip requirements from user query."""
import json
import re
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import get_llm
from state.trip_state import TripState


def user_input_agent(state: TripState) -> dict:
    """Parse and validate user trip requirements from the raw query."""
    llm = get_llm()

    system_prompt = """You are a travel requirements analyst. Extract structured trip information from the user's query.

Return a JSON object with these fields (use null for missing info):
{
  "source": "departure city",
  "destination": "destination city",
  "travel_dates": "date range string",
  "num_days": number_of_days_as_integer,
  "budget": total_budget_in_INR_as_number,
  "num_travelers": number_as_integer,
  "trip_type": "solo|couple|family|business",
  "hotel_preference": "budget|3-star|4-star|5-star|luxury|beach resort|heritage",
  "food_preference": "veg|non-veg|seafood|vegan|any",
  "transport_preference": "flight|train|car|bus|any",
  "places_of_interest": ["list", "of", "interests"],
  "luxury_vs_budget": "luxury|mid-range|budget",
  "special_requirements": "any special notes"
}

For missing budget, estimate based on trip type and duration.
For missing num_travelers, default to 1.
Return ONLY the JSON object, no markdown."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_query"]),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        prefs = json.loads(raw)

        # Ensure required fields have defaults
        prefs.setdefault("num_travelers", 2)
        prefs.setdefault("budget", 30000)
        prefs.setdefault("transport_preference", "any")
        prefs.setdefault("food_preference", "any")
        prefs.setdefault("trip_type", "couple")
        prefs.setdefault("places_of_interest", [])

        # Derive num_days from budget/dates if missing
        if not prefs.get("num_days"):
            prefs["num_days"] = 5

        return {
            "trip_preferences": prefs,
            "messages": [{"role": "system", "content": f"User Input Agent: Extracted preferences for {prefs.get('destination', 'destination')}"}],
            "status": "running",
        }

    except Exception as e:
        # Fallback: parse manually from query text
        prefs = _manual_parse(state["user_query"])
        return {
            "trip_preferences": prefs,
            "error_log": [f"User Input Agent LLM error: {e}"],
            "messages": [{"role": "system", "content": "User Input Agent: Used fallback parsing"}],
            "status": "running",
        }


def _manual_parse(query: str) -> dict:
    """Regex-based fallback parser."""
    q = query.lower()
    days_match = re.search(r"(\d+)[- ]?day", q)
    budget_match = re.search(r"(?:₹|rs\.?|inr)\s?([\d,]+)", q)
    pax_match = re.search(r"(\d+)\s*(?:person|people|traveler|pax)", q)

    return {
        "source": "Bangalore",
        "destination": "Goa",
        "travel_dates": "upcoming",
        "num_days": int(days_match.group(1)) if days_match else 5,
        "budget": int(budget_match.group(1).replace(",", "")) if budget_match else 30000,
        "num_travelers": int(pax_match.group(1)) if pax_match else 2,
        "trip_type": "couple" if "couple" in q else ("family" if "family" in q else "solo"),
        "hotel_preference": "beach resort" if "beach" in q else "3-star",
        "food_preference": "seafood" if "seafood" in q else "any",
        "transport_preference": "flight" if "flight" in q else "any",
        "places_of_interest": [],
        "luxury_vs_budget": "budget",
    }
