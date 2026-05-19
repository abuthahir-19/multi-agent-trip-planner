"""Itinerary Agent — creates a detailed day-wise trip plan using Claude."""
import json
import re
import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from config.settings import get_llm
from state.trip_state import TripState


def itinerary_agent(state: TripState) -> dict:
    """Generate a complete day-by-day itinerary using all gathered data."""
    llm = get_llm(temperature=0.5)

    prefs = state.get("trip_preferences", {})
    weather = state.get("weather_data", {})
    transport = state.get("transport_data", {})
    hotel = state.get("hotel_data", {})
    places = state.get("places_data", {})
    budget = state.get("budget_summary", {})

    context = _build_context(prefs, weather, transport, hotel, places, budget)

    system_prompt = """You are an expert travel itinerary planner. Create a detailed day-wise itinerary.

Return a JSON object with this exact structure:
{
  "trip_title": "descriptive trip title",
  "overview": "2-3 sentence trip overview",
  "days": [
    {
      "day": 1,
      "date": "Day 1 (Arrival)",
      "title": "Arrival & Settle In",
      "activities": [
        {"time": "Morning", "activity": "Activity name", "details": "Details here", "cost": "₹500"},
        {"time": "Afternoon", "activity": "Activity name", "details": "Details here", "cost": "Free"},
        {"time": "Evening", "activity": "Activity name", "details": "Details here", "cost": "₹800"},
        {"time": "Night", "activity": "Dinner", "details": "Local restaurant recommendation", "cost": "₹600"}
      ],
      "notes": "Any tips or notes for this day"
    }
  ],
  "highlights": ["top 3-5 must-do activities"],
  "travel_notes": "important logistical notes"
}

Rules:
- Create exactly the number of days in the trip
- Include check-in/check-out on first/last day
- Balance popular spots with local experiences
- Consider weather conditions
- Keep costs realistic and within budget
- Include food recommendations for each day
Return ONLY the JSON object, no markdown."""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
        itinerary = json.loads(raw)
        return {
            "itinerary": itinerary,
            "messages": [{"role": "system", "content":
                          f"Itinerary Agent: Created {len(itinerary.get('days', []))} day plan — '{itinerary.get('trip_title', '')}'"}],
        }
    except Exception as e:
        itinerary = _fallback_itinerary(prefs, places)
        return {
            "itinerary": itinerary,
            "error_log": [f"Itinerary Agent LLM error: {e}"],
            "messages": [{"role": "system", "content": f"Itinerary Agent: Used fallback template — {e}"}],
        }


def _build_context(prefs, weather, transport, hotel, places, budget) -> str:
    attractions = [a.get("name", "") for a in places.get("top_attractions", [])]
    food_spots = [f.get("name", "") for f in places.get("food_spots", [])]
    recommended_hotel = hotel.get("recommended", {}).get("name", "TBD")
    recommended_transport = transport.get("recommended", "TBD")

    return f"""Trip Details:
- Source: {prefs.get('source', 'N/A')}
- Destination: {prefs.get('destination', 'N/A')}
- Duration: {prefs.get('num_days', 5)} days
- Dates: {prefs.get('travel_dates', 'upcoming')}
- Travelers: {prefs.get('num_travelers', 2)} ({prefs.get('trip_type', 'couple')})
- Budget: ₹{prefs.get('budget', 30000):,}
- Hotel: {recommended_hotel}
- Transport: {recommended_transport}
- Weather: {weather.get('summary', 'Pleasant')}
- Advisory: {weather.get('travel_advisory', '')}

Top Attractions: {', '.join(attractions[:6])}
Food Spots: {', '.join(food_spots[:4])}
Food Preference: {prefs.get('food_preference', 'any')}
Places of Interest: {prefs.get('places_of_interest', [])}
Special Requirements: {prefs.get('special_requirements', 'None')}

Budget Breakdown:
- Transport: ₹{budget.get('breakdown', {}).get('transport', {}).get('total', 0):,}
- Hotel: ₹{budget.get('breakdown', {}).get('accommodation', {}).get('total', 0):,}
- Food: ₹{budget.get('breakdown', {}).get('food', {}).get('total', 0):,}
- Sightseeing: ₹{budget.get('breakdown', {}).get('sightseeing', {}).get('total', 0):,}"""


def _fallback_itinerary(prefs: dict, places: dict) -> dict:
    """Basic itinerary when LLM fails."""
    dest = prefs.get("destination", "Destination")
    num_days = int(prefs.get("num_days", 5))
    attractions = places.get("top_attractions", [])

    days = []
    for i in range(1, num_days + 1):
        if i == 1:
            title = "Arrival & Check-in"
            activities = [
                {"time": "Morning", "activity": "Travel to destination", "details": "Board flight/train", "cost": "Per plan"},
                {"time": "Afternoon", "activity": "Check-in to hotel", "details": f"Settle in at your hotel in {dest}", "cost": "Included"},
                {"time": "Evening", "activity": "Local area walk", "details": "Explore the neighbourhood", "cost": "Free"},
                {"time": "Night", "activity": "Welcome dinner", "details": f"Local cuisine in {dest}", "cost": "₹600-800"},
            ]
        elif i == num_days:
            title = "Checkout & Departure"
            activities = [
                {"time": "Morning", "activity": "Hotel checkout", "details": "Pack and checkout", "cost": "—"},
                {"time": "Afternoon", "activity": "Last-minute shopping", "details": "Buy souvenirs", "cost": "₹500-1,000"},
                {"time": "Evening", "activity": "Departure", "details": "Board return flight/train", "cost": "Per plan"},
            ]
        else:
            attr = attractions[min(i-2, len(attractions)-1)] if attractions else {}
            title = f"Explore {dest}"
            activities = [
                {"time": "Morning", "activity": attr.get("name", f"Sightseeing Day {i}"),
                 "details": attr.get("description", f"Explore {dest}"), "cost": attr.get("entry", "Varies")},
                {"time": "Afternoon", "activity": "Local lunch", "details": "Try local cuisine", "cost": "₹300-500"},
                {"time": "Evening", "activity": "Leisure", "details": "Beach/market/local experience", "cost": "Free"},
                {"time": "Night", "activity": "Dinner", "details": "Restaurant recommendation", "cost": "₹500-800"},
            ]

        days.append({"day": i, "date": f"Day {i}", "title": title, "activities": activities, "notes": ""})

    return {
        "trip_title": f"{num_days}-Day {dest} Adventure",
        "overview": f"A wonderful {num_days}-day trip to {dest}.",
        "days": days,
        "highlights": [a.get("name", "") for a in attractions[:3]],
        "travel_notes": "Book transport and hotels in advance. Carry local currency.",
    }
