"""Transport tool — searches flights/trains/routes (Amadeus API or smart mock)."""
import requests
import json
from config.settings import AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET


def search_transport(source: str, destination: str, travel_dates: str,
                     num_travelers: int, transport_preference: str,
                     budget_per_person: float) -> dict:
    """Search flights, trains, and road routes between source and destination."""
    results = {}

    if transport_preference.lower() in ["flight", "flights", "air", "any"]:
        results["flights"] = _search_flights(source, destination, travel_dates,
                                              num_travelers, budget_per_person)
    if transport_preference.lower() in ["train", "rail", "any"]:
        results["trains"] = _search_trains(source, destination, travel_dates,
                                            num_travelers, budget_per_person)
    if transport_preference.lower() in ["car", "road", "drive", "any"]:
        results["road"] = _road_options(source, destination, num_travelers)

    results["recommended"] = _recommend_transport(results, budget_per_person, num_travelers)
    results["transfer_tips"] = _transfer_tips(destination)
    return results


def _search_flights(source: str, destination: str, dates: str,
                    pax: int, budget_pp: float) -> list:
    """Simulated flight search with realistic data."""
    src = source[:3].upper()
    dst = destination[:3].upper()

    # Map common cities to airport codes
    city_to_code = {
        "bangalore": "BLR", "bengaluru": "BLR", "mumbai": "BOM", "delhi": "DEL",
        "goa": "GOI", "chennai": "MAA", "hyderabad": "HYD", "kolkata": "CCU",
        "jaipur": "JAI", "pune": "PNQ", "ahmedabad": "AMD", "kochi": "COK",
        "london": "LHR", "dubai": "DXB", "singapore": "SIN", "bangkok": "BKK",
        "paris": "CDG", "new york": "JFK", "tokyo": "NRT", "sydney": "SYD",
    }
    src_code = city_to_code.get(source.lower(), src)
    dst_code = city_to_code.get(destination.lower(), dst)

    base_price = max(2500, budget_pp * 0.25)
    flights = [
        {
            "flight_no": f"AI {100 + i}",
            "airline": name,
            "departure": f"{src_code} 06:{str(i*15+00).zfill(2)}",
            "arrival": f"{dst_code} 08:{str(i*10+30).zfill(2)}",
            "duration": f"{1 + i}h {30 - i*5}m",
            "price_per_person": round(base_price * (1 + i * 0.15)),
            "total_price": round(base_price * (1 + i * 0.15) * pax),
            "class": cls,
            "stops": stops,
        }
        for i, (name, cls, stops) in enumerate([
            ("Air India", "Economy", "Non-stop"),
            ("IndiGo", "Economy", "Non-stop"),
            ("SpiceJet", "Economy", "1 stop"),
        ])
    ]
    return flights


def _search_trains(source: str, destination: str, dates: str,
                   pax: int, budget_pp: float) -> list:
    base = max(500, budget_pp * 0.08)
    return [
        {
            "train_no": f"1200{i+1}",
            "name": name,
            "departure": f"{source} {dep}",
            "arrival": f"{destination} {arr}",
            "duration": dur,
            "class": cls,
            "price_per_person": round(base * mult),
            "total_price": round(base * mult * pax),
            "availability": avail,
        }
        for i, (name, dep, arr, dur, cls, mult, avail) in enumerate([
            ("Rajdhani Express", "16:00", "08:00+1", "16h", "AC 2-Tier", 1.0, "Available"),
            ("Shatabdi Express", "06:00", "14:00", "8h", "Chair Car", 0.6, "Available"),
            ("Duronto Express", "22:00", "10:00+1", "12h", "Sleeper", 0.4, "Waitlist"),
        ])
    ]


def _road_options(source: str, destination: str, pax: int) -> dict:
    return {
        "self_drive": {
            "estimated_distance": "500 km",
            "estimated_time": "8-10 hours",
            "fuel_cost": "₹2,500 (approx)",
            "toll_cost": "₹400 (approx)",
        },
        "bus": {
            "operators": ["KSRTC", "VRL Travels", "SRS Travels"],
            "duration": "10-12 hours",
            "price_per_person": "₹600 – ₹1,200",
            "types": ["Sleeper", "Semi-sleeper", "Volvo AC"],
        },
        "cab": {
            "providers": ["Ola Outstation", "Uber Intercity", "Local taxi"],
            "estimated_cost": f"₹{3000 + pax * 200} – ₹{5000 + pax * 300}",
            "duration": "8-9 hours",
        },
    }


def _recommend_transport(results: dict, budget_pp: float, pax: int) -> str:
    if "flights" in results and results["flights"]:
        cheapest = min(results["flights"], key=lambda x: x["price_per_person"])
        if cheapest["price_per_person"] <= budget_pp * 0.3:
            return (f"Recommended: {cheapest['airline']} flight "
                    f"({cheapest['flight_no']}) — ₹{cheapest['price_per_person']:,}/person. "
                    "Best value for time saved.")
    if "trains" in results and results["trains"]:
        train = results["trains"][0]
        return (f"Recommended: {train['name']} ({train['class']}) — "
                f"₹{train['price_per_person']:,}/person. Comfortable and scenic.")
    return "Recommended: Check bus operators for budget-friendly travel."


def _transfer_tips(destination: str) -> list:
    return [
        f"Pre-book airport/station transfers to {destination} to avoid surge pricing.",
        "Use prepaid taxi counters at the airport for fixed rates.",
        "Download Ola/Uber app for local transport within the city.",
        "Metro/public transport is cheapest for city sightseeing.",
        "Negotiate auto/rickshaw fares before boarding.",
    ]
