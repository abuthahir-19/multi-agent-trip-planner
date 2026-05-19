"""Final Review Agent — validates the complete plan and detects conflicts."""
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import get_llm
from state.trip_state import TripState
import json
import re


def review_agent(state: TripState) -> dict:
    """Validate the trip plan for completeness, accuracy, and conflicts."""
    llm = get_llm(temperature=0.2)

    prefs = state.get("trip_preferences", {})
    transport = state.get("transport_data", {})
    hotel = state.get("hotel_data", {})
    budget = state.get("budget_summary", {})
    itinerary = state.get("itinerary", {})
    weather = state.get("weather_data", {})

    system_prompt = """You are a quality control agent for AI-generated travel plans.
Review the trip plan and return a JSON object:
{
  "approved": true|false,
  "quality_score": 0-100,
  "completeness_check": {
    "transport": true|false,
    "hotel": true|false,
    "itinerary": true|false,
    "budget": true|false,
    "places": true|false
  },
  "conflicts": ["list any conflicts found"],
  "retry_agents": ["agent names that need to rerun"],
  "recommendations": ["improvement suggestions"],
  "final_notes": "overall assessment"
}

Approve (approved=true) if:
- All sections have data
- Budget is not more than 50% over limit
- Itinerary has correct number of days
- No major conflicts

Return ONLY the JSON, no markdown."""

    review_context = f"""Trip Plan Summary:
Destination: {prefs.get('destination')}
Days: {prefs.get('num_days')}
Budget: ₹{prefs.get('budget', 0):,}
Estimated Cost: ₹{budget.get('total_estimated', 0):,}
Over Budget: {budget.get('over_budget', False)}

Transport: {"Available" if not transport.get('error') else f"Error: {transport.get('error')}"}
Hotel: {"Recommended: " + hotel.get('recommended', {}).get('name', 'N/A') if not hotel.get('error') else f"Error: {hotel.get('error')}"}
Itinerary Days: {len(itinerary.get('days', []))} (expected {prefs.get('num_days', 5)})
Weather: {weather.get('summary', 'N/A')}
Errors so far: {state.get('error_log', [])}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=review_context),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        review = json.loads(raw)
    except Exception as e:
        review = _fallback_review(state)
        review["error"] = str(e)

    approved = review.get("approved", False)
    score = review.get("quality_score", 0)

    return {
        "review_status": review,
        "messages": [{"role": "system", "content":
                      f"Review Agent: {'APPROVED' if approved else 'REJECTED'} — Score: {score}/100. "
                      f"Conflicts: {review.get('conflicts', [])}"}],
    }


def _fallback_review(state: TripState) -> dict:
    """Simple rule-based review when LLM fails."""
    transport = state.get("transport_data", {})
    hotel = state.get("hotel_data", {})
    itinerary = state.get("itinerary", {})
    budget = state.get("budget_summary", {})
    prefs = state.get("trip_preferences", {})

    conflicts = []
    retry_agents = []

    if transport.get("error"):
        conflicts.append("Transport data unavailable")
        retry_agents.append("transport_agent")

    if hotel.get("error"):
        conflicts.append("Hotel data unavailable")
        retry_agents.append("hotel_agent")

    actual_days = len(itinerary.get("days", []))
    expected_days = int(prefs.get("num_days", 5))
    if actual_days != expected_days:
        conflicts.append(f"Itinerary has {actual_days} days but trip is {expected_days} days")
        retry_agents.append("itinerary_agent")

    over_budget = budget.get("over_budget", False)
    if over_budget:
        deficit = abs(budget.get("savings_or_deficit", 0))
        if deficit > budget.get("total_budget", 1) * 0.5:
            conflicts.append(f"Budget significantly exceeded by ₹{deficit:,}")
            retry_agents.append("hotel_agent")

    approved = len(conflicts) == 0 and not (transport.get("error") or hotel.get("error"))
    score = max(50, 100 - len(conflicts) * 15)

    return {
        "approved": approved,
        "quality_score": score,
        "completeness_check": {
            "transport": not bool(transport.get("error")),
            "hotel": not bool(hotel.get("error")),
            "itinerary": actual_days == expected_days,
            "budget": not over_budget,
            "places": bool(state.get("places_data")),
        },
        "conflicts": conflicts,
        "retry_agents": retry_agents,
        "recommendations": ["All sections completed successfully."] if not conflicts else conflicts,
        "final_notes": "Plan approved" if approved else f"Issues found: {', '.join(conflicts)}",
    }
