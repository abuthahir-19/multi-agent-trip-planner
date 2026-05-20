"""Hotel tool — searches accommodations within budget (smart mock data)."""


def search_hotels(destination: str, check_in: str, check_out: str,
                  num_travelers: int, budget_per_night: float,
                  hotel_preference: str, trip_type: str) -> dict:
    """Search hotels matching the user's budget and preferences."""

    hotels = _generate_hotels(destination, hotel_preference, trip_type)
    filtered = [h for h in hotels if h["price_per_night"] <= budget_per_night * 1.2]
    if not filtered:
        filtered = hotels[:3]

    filtered.sort(key=lambda h: (
        abs(h["price_per_night"] - budget_per_night),
        -h["rating"]
    ))

    return {
        "destination": destination,
        "check_in": check_in,
        "check_out": check_out,
        "travelers": num_travelers,
        "budget_per_night": budget_per_night,
        "hotels": filtered[:5],
        "recommended": filtered[0] if filtered else None,
        "booking_tips": _booking_tips(destination),
    }


def _generate_hotels(destination: str, preference: str, trip_type: str) -> list:
    dest = destination.lower()

    beach_areas = {
        "goa": ["Calangute", "Baga", "Anjuna", "Panjim"],
        "phuket": ["Patong", "Kamala", "Kata"],
        "bali": ["Seminyak", "Ubud", "Kuta"],
    }
    areas = next((v for k, v in beach_areas.items() if k in dest), [destination, f"Central {destination}"])

    pref_lower = preference.lower()
    is_luxury = "luxury" in pref_lower or "5 star" in pref_lower or trip_type.lower() == "couple"
    is_budget = "budget" in pref_lower or "hostel" in pref_lower

    base = 8000 if is_luxury else (1500 if is_budget else 3500)

    hotels = [
        {
            "name": f"The {destination.title()} Grand Resort",
            "area": areas[0] if areas else destination,
            "category": "5-Star Luxury Resort",
            "rating": 4.8,
            "price_per_night": base * 2.5,
            "amenities": ["Pool", "Spa", "Beach Access", "Gym", "Restaurant", "Bar", "WiFi"],
            "room_types": ["Deluxe Room", "Suite", "Beach Villa"],
            "reviews": "Stunning views, impeccable service. Perfect for couples.",
            "booking_link": "Booking.com / MakeMyTrip",
        },
        {
            "name": f"{destination.title()} Boutique Inn",
            "area": areas[min(1, len(areas)-1)] if areas else destination,
            "category": "4-Star Boutique Hotel",
            "rating": 4.5,
            "price_per_night": base * 1.4,
            "amenities": ["Pool", "Restaurant", "WiFi", "Free Breakfast"],
            "room_types": ["Standard Room", "Deluxe Room"],
            "reviews": "Charming property with great location and friendly staff.",
            "booking_link": "Booking.com / Airbnb",
        },
        {
            "name": f"Comfort Stay {destination.title()}",
            "area": areas[min(1, len(areas)-1)] if areas else destination,
            "category": "3-Star Hotel",
            "rating": 4.2,
            "price_per_night": base * 0.8,
            "amenities": ["WiFi", "Restaurant", "24/7 Front Desk", "Parking"],
            "room_types": ["Standard", "Deluxe"],
            "reviews": "Clean, comfortable, and great value for money.",
            "booking_link": "Booking.com / OYO",
        },
        {
            "name": f"Beach Backpackers {destination.title()}",
            "area": areas[0] if areas else destination,
            "category": "Budget Hostel/Guesthouse",
            "rating": 4.0,
            "price_per_night": base * 0.35,
            "amenities": ["WiFi", "Common Kitchen", "Locker", "Terrace"],
            "room_types": ["Dorm Bed", "Private Room"],
            "reviews": "Perfect for solo travellers. Great social atmosphere.",
            "booking_link": "HostelWorld / Booking.com",
        },
        {
            "name": f"Heritage Haveli {destination.title()}",
            "area": areas[0] if areas else destination,
            "category": "Heritage Property",
            "rating": 4.6,
            "price_per_night": base * 1.8,
            "amenities": ["Pool", "Ayurveda Spa", "Yoga", "Restaurant", "WiFi"],
            "room_types": ["Heritage Room", "Royal Suite"],
            "reviews": "Authentic local experience with modern comforts. Highly recommended.",
            "booking_link": "MakeMyTrip / Booking.com",
        },
    ]
    return hotels


def _booking_tips(destination: str) -> list:
    return [
        "Book at least 2-3 weeks in advance for peak season to get best rates.",
        "Compare prices on Booking.com, MakeMyTrip, and direct hotel websites.",
        "Check cancellation policy — opt for free cancellation when possible.",
        "Request early check-in/late check-out during booking to save on extra nights.",
        f"Look for hotels near {destination}'s main attractions to save on transport.",
        "Read recent reviews (last 3 months) for accurate current information.",
    ]
