"""Hotel tool — RapidAPI Booking.com (live) with smart mock fallback.

Live data:  set RAPIDAPI_KEY in .env  →  real Booking.com listings
Mock data:  RAPIDAPI_KEY absent/blank  →  generated realistic data
"""
import requests
from config.settings import RAPIDAPI_KEY

_BOOKING_HOST = "booking-com.p.rapidapi.com"
_HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": _BOOKING_HOST,
}
_TIMEOUT = 10


def search_hotels(destination: str, check_in: str, check_out: str,
                  num_travelers: int, budget_per_night: float,
                  hotel_preference: str, trip_type: str) -> dict:
    """Search hotels — uses Booking.com live API when RAPIDAPI_KEY is set."""
    source = "live" if RAPIDAPI_KEY else "mock"

    if RAPIDAPI_KEY:
        hotels, source = _live_hotels(destination, check_in, check_out,
                                      num_travelers, hotel_preference)
    else:
        hotels = []

    if not hotels:
        hotels = _generate_mock_hotels(destination, hotel_preference, trip_type)
        source = "mock"

    filtered = [h for h in hotels if h["price_per_night"] <= budget_per_night * 1.3]
    if not filtered:
        filtered = hotels[:3]

    filtered.sort(key=lambda h: (
        abs(h["price_per_night"] - budget_per_night),
        -h["rating"],
    ))

    return {
        "destination":      destination,
        "check_in":         check_in,
        "check_out":        check_out,
        "travelers":        num_travelers,
        "budget_per_night": budget_per_night,
        "hotels":           filtered[:5],
        "recommended":      filtered[0] if filtered else None,
        "booking_tips":     _booking_tips(destination),
        "data_source":      source,
    }


# ─────────────────────────────────────────────────────────────────
# Live API — Booking.com via RapidAPI
# ─────────────────────────────────────────────────────────────────

def _live_hotels(destination: str, check_in: str, check_out: str,
                 num_travelers: int, preference: str):
    """Fetch real hotels from Booking.com RapidAPI. Returns (list, source_label)."""
    try:
        dest_id, dest_type = _get_dest_id(destination)
        if not dest_id:
            return [], "mock"

        check_in_fmt  = _parse_date(check_in)
        check_out_fmt = _parse_date(check_out)
        if not check_in_fmt or not check_out_fmt:
            return [], "mock"

        params = {
            "dest_id":             dest_id,
            "dest_type":           dest_type,
            "checkin_date":        check_in_fmt,
            "checkout_date":       check_out_fmt,
            "adults_number":       str(max(1, num_travelers)),
            "room_number":         "1",
            "order_by":            "price",
            "filter_by_currency":  "INR",
            "locale":              "en-gb",
            "units":               "metric",
            "page_number":         "0",
            "include_adjacency":   "true",
        }

        resp = requests.get(
            f"https://{_BOOKING_HOST}/v1/hotels/search",
            headers=_HEADERS, params=params, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        hotels = [_normalise_booking(h) for h in data.get("result", [])[:10]]
        hotels = [h for h in hotels if h]
        return hotels, "live (Booking.com)"

    except Exception as e:
        if RAPIDAPI_KEY:
            print(f"[Hotels] Booking.com API error: {e} — falling back to mock")
        return [], "mock"


def _get_dest_id(destination: str):
    """Resolve city name → Booking.com dest_id and dest_type."""
    try:
        resp = requests.get(
            f"https://{_BOOKING_HOST}/v1/hotels/locations",
            headers=_HEADERS,
            params={"name": destination, "locale": "en-gb"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None, None
        # prefer city-level result
        for r in results:
            if r.get("dest_type") in ("city", "district", "region"):
                return r["dest_id"], r["dest_type"]
        return results[0]["dest_id"], results[0].get("dest_type", "city")
    except Exception:
        return None, None


def _normalise_booking(raw: dict) -> dict | None:
    """Convert Booking.com hotel object to our standard format."""
    try:
        price_info = raw.get("price_breakdown", {})
        price = float(price_info.get("gross_price", 0) or
                      raw.get("min_total_price", 0) or 0)
        if price <= 0:
            return None

        stars = int(raw.get("class", 0) or 0)
        category_map = {5: "5-Star Luxury", 4: "4-Star Hotel",
                        3: "3-Star Hotel", 2: "Budget Hotel", 1: "Guesthouse"}

        facilities_raw = raw.get("hotel_facilities", "") or ""
        amenities = [f.strip() for f in facilities_raw.split(",")
                     if f.strip()][:6] or ["WiFi", "Restaurant"]

        return {
            "name":            raw.get("hotel_name", "Hotel"),
            "area":            raw.get("district", raw.get("city", "")),
            "location":        raw.get("city", ""),
            "category":        category_map.get(stars, f"{stars}-Star Hotel"),
            "rating":          round(float(raw.get("review_score", 0) or 0) / 2, 1),
            "price_per_night": round(price),
            "amenities":       amenities,
            "room_types":      ["Standard Room", "Deluxe Room"],
            "reviews":         raw.get("review_score_word", "Good"),
            "booking_link":    raw.get("url", "booking.com"),
            "address":         raw.get("address", ""),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Mock fallback
# ─────────────────────────────────────────────────────────────────

def _generate_mock_hotels(destination: str, preference: str, trip_type: str) -> list:
    dest = destination.lower()
    beach_areas = {
        "goa":    ["Calangute", "Baga", "Anjuna", "Panjim"],
        "phuket": ["Patong", "Kamala", "Kata"],
        "bali":   ["Seminyak", "Ubud", "Kuta"],
    }
    areas = next((v for k, v in beach_areas.items() if k in dest),
                 [destination, f"Central {destination}"])

    pref_lower = preference.lower()
    is_luxury = "luxury" in pref_lower or "5" in pref_lower
    is_budget  = "budget" in pref_lower or "hostel" in pref_lower
    base = 8000 if is_luxury else (1500 if is_budget else 3500)

    return [
        {
            "name":            f"The {destination.title()} Grand Resort",
            "area":            areas[0],
            "location":        destination,
            "category":        "5-Star Luxury Resort",
            "rating":          4.8,
            "price_per_night": round(base * 2.5),
            "amenities":       ["Pool", "Spa", "Beach Access", "Gym", "Restaurant", "Bar", "WiFi"],
            "room_types":      ["Deluxe Room", "Suite", "Beach Villa"],
            "reviews":         "Stunning views, impeccable service.",
            "booking_link":    "booking.com / MakeMyTrip",
        },
        {
            "name":            f"{destination.title()} Boutique Inn",
            "area":            areas[min(1, len(areas)-1)],
            "location":        destination,
            "category":        "4-Star Boutique Hotel",
            "rating":          4.5,
            "price_per_night": round(base * 1.4),
            "amenities":       ["Pool", "Restaurant", "WiFi", "Free Breakfast"],
            "room_types":      ["Standard Room", "Deluxe Room"],
            "reviews":         "Charming property, great location.",
            "booking_link":    "booking.com / Airbnb",
        },
        {
            "name":            f"Comfort Stay {destination.title()}",
            "area":            areas[min(1, len(areas)-1)],
            "location":        destination,
            "category":        "3-Star Hotel",
            "rating":          4.2,
            "price_per_night": round(base * 0.8),
            "amenities":       ["WiFi", "Restaurant", "24/7 Front Desk", "Parking"],
            "room_types":      ["Standard", "Deluxe"],
            "reviews":         "Clean, comfortable, great value.",
            "booking_link":    "booking.com / OYO",
        },
        {
            "name":            f"Beach Backpackers {destination.title()}",
            "area":            areas[0],
            "location":        destination,
            "category":        "Budget Hostel",
            "rating":          4.0,
            "price_per_night": round(base * 0.35),
            "amenities":       ["WiFi", "Common Kitchen", "Locker", "Terrace"],
            "room_types":      ["Dorm Bed", "Private Room"],
            "reviews":         "Perfect for solo travellers.",
            "booking_link":    "hostelworld.com / booking.com",
        },
        {
            "name":            f"Heritage Haveli {destination.title()}",
            "area":            areas[0],
            "location":        destination,
            "category":        "Heritage Property",
            "rating":          4.6,
            "price_per_night": round(base * 1.8),
            "amenities":       ["Pool", "Ayurveda Spa", "Yoga", "Restaurant", "WiFi"],
            "room_types":      ["Heritage Room", "Royal Suite"],
            "reviews":         "Authentic experience with modern comforts.",
            "booking_link":    "MakeMyTrip / booking.com",
        },
    ]


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _parse_date(date_str: str) -> str | None:
    """Try to extract a YYYY-MM-DD from various date string formats."""
    import re
    from datetime import datetime, timedelta

    if not date_str:
        return None

    # Already ISO format
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)

    # "June 10 to June 15, 2025" → take first date
    months = {"january":"01","february":"02","march":"03","april":"04",
              "may":"05","june":"06","july":"07","august":"08",
              "september":"09","october":"10","november":"11","december":"12"}
    s = date_str.lower()
    for mon, num in months.items():
        m = re.search(rf"{mon}\s+(\d{{1,2}})[,\s]+(\d{{4}})", s)
        if m:
            return f"{m.group(2)}-{num}-{int(m.group(1)):02d}"

    # Fallback: 30 days from today
    future = datetime.today() + timedelta(days=30)
    return future.strftime("%Y-%m-%d")


def _booking_tips(destination: str) -> list:
    return [
        "Book 2–3 weeks in advance for peak season.",
        "Compare prices on Booking.com, MakeMyTrip, and hotel's own website.",
        "Choose free-cancellation rates when available.",
        "Request early check-in/late check-out at the time of booking.",
        f"Stay near {destination}'s main attractions to reduce transport costs.",
        "Read reviews from the last 3 months for accurate current conditions.",
    ]
