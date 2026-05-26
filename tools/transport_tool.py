"""Transport tool — RapidAPI Skyscanner (live flights) with smart mock fallback.

Live data:  set RAPIDAPI_KEY in .env  →  real Skyscanner flight prices
Mock data:  RAPIDAPI_KEY absent/blank  →  generated realistic data

Trains and road options always use smart mock (no free real-time API available).
"""
import re
import requests
from config.settings import RAPIDAPI_KEY

_SKYSCANNER_HOST = "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com"
_HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": _SKYSCANNER_HOST,
}
_TIMEOUT = 10

# IATA airport codes for common Indian and international cities
_CITY_TO_IATA = {
    "bangalore": "BLR", "bengaluru": "BLR",
    "mumbai": "BOM", "bombay": "BOM",
    "delhi": "DEL", "new delhi": "DEL",
    "goa": "GOI", "dabolim": "GOI",
    "chennai": "MAA", "madras": "MAA",
    "hyderabad": "HYD",
    "kolkata": "CCU", "calcutta": "CCU",
    "jaipur": "JAI",
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "kochi": "COK", "cochin": "COK",
    "lucknow": "LKO",
    "varanasi": "VNS",
    "amritsar": "ATQ",
    "guwahati": "GAU",
    "bhubaneswar": "BBI",
    "nagpur": "NAG",
    "indore": "IDR",
    "srinagar": "SXR",
    "leh": "IXL",
    "port blair": "IXZ",
    "london": "LHR",
    "dubai": "DXB",
    "singapore": "SIN",
    "bangkok": "BKK",
    "paris": "CDG",
    "new york": "JFK",
    "tokyo": "NRT",
    "sydney": "SYD",
}


def search_transport(source: str, destination: str, travel_dates: str,
                     num_travelers: int, transport_preference: str,
                     budget_per_person: float) -> dict:
    """Search flights, trains, and road routes."""
    results = {}
    pref = transport_preference.lower()

    if pref in ("flight", "flights", "air", "any"):
        results["flights"] = _search_flights(source, destination, travel_dates,
                                              num_travelers, budget_per_person)
    if pref in ("train", "rail", "any"):
        results["trains"] = _search_trains(source, destination, travel_dates,
                                            num_travelers, budget_per_person)
    if pref in ("car", "road", "drive", "any"):
        results["road"] = _road_options(source, destination, num_travelers)

    results["recommended"]   = _recommend_transport(results, budget_per_person)
    results["transfer_tips"] = _transfer_tips(destination)
    return results


# ─────────────────────────────────────────────────────────────────
# Flights — Skyscanner live → mock fallback
# ─────────────────────────────────────────────────────────────────

def _search_flights(source: str, destination: str, dates: str,
                    pax: int, budget_pp: float) -> list:
    if RAPIDAPI_KEY:
        flights = _live_flights(source, destination, dates, pax)
        if flights:
            return flights
        print("[Transport] Skyscanner API failed — falling back to mock flights")
    return _mock_flights(source, destination, pax, budget_pp)


def _live_flights(source: str, destination: str, dates: str, pax: int) -> list:
    """Fetch real flight prices from Skyscanner via RapidAPI."""
    try:
        src_code  = _city_to_iata(source)
        dst_code  = _city_to_iata(destination)
        date_str  = _extract_date(dates)

        url = (
            f"https://{_SKYSCANNER_HOST}/browseroutes/v1.0"
            f"/IN/INR/en-US/{src_code}-sky/{dst_code}-sky/{date_str}"
        )
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        quotes   = data.get("Quotes", [])
        carriers = {c["CarrierId"]: c["Name"]
                    for c in data.get("Carriers", [])}
        places   = {p["PlaceId"]: p.get("IataCode", p.get("Name", ""))
                    for p in data.get("Places", [])}

        flights = []
        for i, q in enumerate(quotes[:5]):
            outbound = q.get("OutboundLeg", {})
            carrier_ids = outbound.get("CarrierIds", [])
            airline = carriers.get(carrier_ids[0], "Airline") if carrier_ids else "Airline"
            price_pp = int(q.get("MinPrice", 0))
            if price_pp <= 0:
                continue

            origin_id = outbound.get("OriginId")
            dest_id   = outbound.get("DestinationId")
            dep_iata  = places.get(origin_id, src_code)
            arr_iata  = places.get(dest_id,   dst_code)
            dep_time  = outbound.get("DepartureDate", "")[:10]

            flights.append({
                "flight_no":        f"{airline[:2].upper()}{100 + i}",
                "airline":          airline,
                "departure":        f"{dep_iata} {dep_time}",
                "arrival":          arr_iata,
                "arrival_city":     destination,
                "duration":         "~2h",
                "price_per_person": price_pp,
                "total_price":      price_pp * pax,
                "class":            "Economy",
                "stops":            "Non-stop" if q.get("Direct") else "1 stop",
                "data_source":      "live (Skyscanner)",
            })

        return flights

    except Exception as e:
        if RAPIDAPI_KEY:
            print(f"[Transport] Skyscanner error: {e}")
        return []


def _mock_flights(source: str, destination: str, pax: int, budget_pp: float) -> list:
    src_code = _city_to_iata(source)
    dst_code = _city_to_iata(destination)
    base     = max(2500, budget_pp * 0.25)

    airlines = [
        ("Air India",  "Economy", "Non-stop"),
        ("IndiGo",     "Economy", "Non-stop"),
        ("SpiceJet",   "Economy", "1 stop"),
    ]
    return [
        {
            "flight_no":        f"AI{100 + i}",
            "airline":          name,
            "departure":        f"{src_code} 06:{i*15:02d}",
            "arrival":          f"{dst_code} 08:{30 + i*10:02d}",
            "arrival_city":     destination,
            "duration":         f"{1 + i}h {30 - i*5}m",
            "price_per_person": round(base * (1 + i * 0.15)),
            "total_price":      round(base * (1 + i * 0.15) * pax),
            "class":            cls,
            "stops":            stops,
            "data_source":      "mock",
        }
        for i, (name, cls, stops) in enumerate(airlines)
    ]


# ─────────────────────────────────────────────────────────────────
# Trains — always mock (no free real-time Indian rail API)
# ─────────────────────────────────────────────────────────────────

def _search_trains(source: str, destination: str, dates: str,
                   pax: int, budget_pp: float) -> list:
    base = max(500, budget_pp * 0.08)
    trains = [
        ("Rajdhani Express",  "16:00", "08:00+1", "16h", "AC 2-Tier",  1.0,  "Available"),
        ("Shatabdi Express",  "06:00", "14:00",   "8h",  "Chair Car",  0.6,  "Available"),
        ("Duronto Express",   "22:00", "10:00+1", "12h", "Sleeper",    0.4,  "Waitlist"),
    ]
    return [
        {
            "train_no":         f"1200{i+1}",
            "name":             name,
            "departure":        f"{source} {dep}",
            "arrival":          f"{destination} {arr}",
            "duration":         dur,
            "class":            cls,
            "price_per_person": round(base * mult),
            "total_price":      round(base * mult * pax),
            "availability":     avail,
            "data_source":      "mock",
        }
        for i, (name, dep, arr, dur, cls, mult, avail) in enumerate(trains)
    ]


# ─────────────────────────────────────────────────────────────────
# Road — always mock
# ─────────────────────────────────────────────────────────────────

def _road_options(source: str, destination: str, pax: int) -> dict:
    return {
        "self_drive": {
            "estimated_distance": "500 km",
            "estimated_time":     "8–10 hours",
            "fuel_cost":          "₹2,500 approx",
            "toll_cost":          "₹400 approx",
        },
        "bus": {
            "operators":          ["KSRTC", "VRL Travels", "SRS Travels"],
            "duration":           "10–12 hours",
            "price_per_person":   "₹600 – ₹1,200",
            "types":              ["Sleeper", "Semi-sleeper", "Volvo AC"],
        },
        "cab": {
            "providers":      ["Ola Outstation", "Uber Intercity", "Local taxi"],
            "estimated_cost": f"₹{3000 + pax * 200} – ₹{5000 + pax * 300}",
            "duration":       "8–9 hours",
        },
    }


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _city_to_iata(city: str) -> str:
    """Return IATA code for a city, or first 3 uppercase letters as fallback."""
    return _CITY_TO_IATA.get(city.lower().strip(), city[:3].upper())


def _extract_date(date_str: str) -> str:
    """Pull first YYYY-MM-DD from a free-text date string."""
    from datetime import datetime, timedelta

    if not date_str:
        return (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)

    months = {
        "january":"01","february":"02","march":"03","april":"04",
        "may":"05","june":"06","july":"07","august":"08",
        "september":"09","october":"10","november":"11","december":"12",
    }
    s = date_str.lower()
    for mon, num in months.items():
        m = re.search(rf"{mon}\s+(\d{{1,2}})[,\s]+(\d{{4}})", s)
        if m:
            return f"{m.group(2)}-{num}-{int(m.group(1)):02d}"

    return (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")


def _recommend_transport(results: dict, budget_pp: float) -> str:
    if "flights" in results and results["flights"]:
        cheapest = min(results["flights"], key=lambda x: x["price_per_person"])
        if cheapest["price_per_person"] <= budget_pp * 0.35:
            src = cheapest.get("data_source", "")
            tag = " (live price)" if "live" in src else ""
            return (f"{cheapest['airline']} {cheapest['flight_no']}{tag} — "
                    f"₹{cheapest['price_per_person']:,}/person. Best value for time saved.")
    if "trains" in results and results["trains"]:
        t = results["trains"][0]
        return f"{t['name']} ({t['class']}) — ₹{t['price_per_person']:,}/person."
    return "Check bus operators for the most budget-friendly option."


def _transfer_tips(destination: str) -> list:
    return [
        f"Pre-book airport/station transfers to {destination} to avoid surge pricing.",
        "Use prepaid taxi counters at airports for fixed rates.",
        "Download Ola/Uber for local transport within the city.",
        "Metro/public transport is cheapest for sightseeing.",
        "Negotiate auto-rickshaw fares before boarding.",
    ]
