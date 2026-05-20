"""Places Explorer tool — tourist attractions, local food, and experiences."""


def explore_places(destination: str, places_of_interest: list,
                   trip_type: str, food_preferences: str,
                   weather_condition: str = "") -> dict:
    """Return tourist attractions, local food, and experiences for a destination."""
    attractions = _get_attractions(destination, places_of_interest, trip_type, weather_condition)
    food_spots = _get_food_spots(destination, food_preferences)
    local_experiences = _get_local_experiences(destination, trip_type)
    emergency_info = _get_emergency_info(destination)

    return {
        "destination": destination,
        "top_attractions": attractions,
        "food_spots": food_spots,
        "local_experiences": local_experiences,
        "emergency_info": emergency_info,
        "travel_tips": _travel_tips(destination, trip_type),
        "packing_checklist": _packing_checklist(destination, weather_condition),
    }


def _get_attractions(destination: str, interests: list, trip_type: str,
                     weather: str) -> list:
    dest = destination.lower()
    rainy = "rain" in weather.lower() or "storm" in weather.lower()

    # Generic attraction templates enriched per destination
    base_attractions = {
        "goa": [
            {"name": "Baga Beach", "type": "Beach", "entry": "Free",
             "best_time": "Evening", "rating": 4.5, "duration": "3-4 hrs",
             "indoor": False, "description": "Iconic beach with water sports and beach shacks."},
            {"name": "Fort Aguada", "type": "Heritage", "entry": "₹30",
             "best_time": "Morning", "rating": 4.3, "duration": "2 hrs",
             "indoor": False, "description": "16th-century Portuguese fort with lighthouse and ocean views."},
            {"name": "Basilica of Bom Jesus", "type": "Religious", "entry": "Free",
             "best_time": "Morning", "rating": 4.7, "duration": "1.5 hrs",
             "indoor": True, "description": "UNESCO World Heritage church housing the tomb of St. Francis Xavier."},
            {"name": "Dudhsagar Falls", "type": "Nature", "entry": "₹400",
             "best_time": "Monsoon", "rating": 4.8, "duration": "Full day",
             "indoor": False, "description": "Spectacular four-tiered waterfall on the Goa–Karnataka border."},
            {"name": "Anjuna Flea Market", "type": "Shopping", "entry": "Free",
             "best_time": "Wednesday afternoon", "rating": 4.2, "duration": "2-3 hrs",
             "indoor": False, "description": "Famous weekly market for souvenirs, clothes, and local crafts."},
            {"name": "Nightlife at Tito's Lane", "type": "Nightlife", "entry": "Varies",
             "best_time": "Night", "rating": 4.4, "duration": "Evening",
             "indoor": True, "description": "Goa's most famous strip of bars, clubs, and live music venues."},
        ],
        "default": [
            {"name": f"{destination.title()} Old Town", "type": "Heritage",
             "entry": "Free", "best_time": "Morning", "rating": 4.4,
             "duration": "2-3 hrs", "indoor": False,
             "description": f"Explore the historical heart of {destination}."},
            {"name": f"{destination.title()} National Museum", "type": "Museum",
             "entry": "₹200", "best_time": "Anytime", "rating": 4.3,
             "duration": "2-3 hrs", "indoor": True,
             "description": f"Rich collection of art and history of {destination}."},
            {"name": f"{destination.title()} Viewpoint", "type": "Scenic",
             "entry": "Free", "best_time": "Sunrise/Sunset", "rating": 4.7,
             "duration": "1-2 hrs", "indoor": False,
             "description": f"Panoramic views of {destination} and surroundings."},
            {"name": f"Local Market of {destination.title()}", "type": "Shopping",
             "entry": "Free", "best_time": "Morning", "rating": 4.1,
             "duration": "1-2 hrs", "indoor": False,
             "description": "Vibrant local bazaar with handicrafts and street food."},
            {"name": f"{destination.title()} Adventure Park", "type": "Adventure",
             "entry": "₹800", "best_time": "Morning", "rating": 4.5,
             "duration": "3-4 hrs", "indoor": False,
             "description": "Thrilling outdoor activities including zip-lining and trekking."},
        ]
    }

    attractions = base_attractions.get(dest, base_attractions["default"])

    # Filter out outdoor activities if rainy weather
    if rainy:
        attractions = [a for a in attractions if a.get("indoor", False) or a["type"] in ["Museum", "Religious"]]
        if not attractions:
            attractions = base_attractions.get(dest, base_attractions["default"])

    # Filter by interests if provided
    if interests:
        interest_lower = [i.lower() for i in interests]
        filtered = [a for a in attractions if any(i in a["type"].lower() for i in interest_lower)]
        if filtered:
            attractions = filtered + [a for a in attractions if a not in filtered]

    return attractions[:6]


def _get_food_spots(destination: str, food_pref: str) -> list:
    dest = destination.lower()
    pref = food_pref.lower()

    food_data = {
        "goa": [
            {"name": "Brittos", "cuisine": "Seafood/Goan", "price": "₹800-1,200/person",
             "must_try": ["Fish Thali", "Prawn Curry", "Bebinca"], "rating": 4.5,
             "type": "Restaurant"},
            {"name": "Fisherman's Wharf", "cuisine": "Seafood", "price": "₹1,000-1,500/person",
             "must_try": ["Pomfret Recheado", "Grilled Lobster"], "rating": 4.6,
             "type": "Restaurant"},
            {"name": "Beach Shacks (Baga/Calangute)", "cuisine": "Multi-cuisine/Seafood",
             "price": "₹500-800/person", "must_try": ["Kingfish fry", "Beer & sunset views"],
             "rating": 4.3, "type": "Beach Shack"},
            {"name": "Cafe Tato", "cuisine": "Local Goan", "price": "₹150-300/person",
             "must_try": ["Pao Bhaji", "Ros Omelette"], "rating": 4.4, "type": "Local Cafe"},
        ],
        "default": [
            {"name": f"{destination.title()} Food Street", "cuisine": "Local/Street Food",
             "price": "₹200-500/person", "must_try": ["Local specialty", "Street snacks"],
             "rating": 4.3, "type": "Street Food"},
            {"name": f"The {destination.title()} Kitchen", "cuisine": "Local/Continental",
             "price": "₹600-1,000/person", "must_try": ["Regional thali", "Local dessert"],
             "rating": 4.5, "type": "Restaurant"},
            {"name": "Rooftop Dining Hub", "cuisine": "Multi-cuisine",
             "price": "₹800-1,200/person", "must_try": ["Chef's special", "Local cocktails"],
             "rating": 4.4, "type": "Restaurant"},
        ]
    }

    spots = food_data.get(dest, food_data["default"])

    # Filter by preference
    if "veg" in pref or "vegetarian" in pref:
        spots = [s for s in spots if "seafood" not in s["cuisine"].lower()] or spots
    elif "seafood" in pref:
        spots = [s for s in spots if "seafood" in s["cuisine"].lower()] + \
                [s for s in spots if "seafood" not in s["cuisine"].lower()]

    return spots[:4]


def _get_local_experiences(destination: str, trip_type: str) -> list:
    experiences = [
        f"Sunrise/Sunset at a scenic point in {destination}",
        f"Cooking class to learn {destination}'s local cuisine",
        f"Local heritage walk with a guide",
        "Interact with local artisans and buy authentic handicrafts",
        f"Rent a two-wheeler and explore {destination} at your own pace",
    ]
    if trip_type.lower() == "couple":
        experiences += ["Beachside candlelit dinner", "Couples spa at a resort"]
    elif trip_type.lower() == "family":
        experiences += ["Kids activity park", "Cultural show and folk dance performance"]
    elif trip_type.lower() == "solo":
        experiences += ["Solo trekking", "Hostel social events and backpacker meetups"]
    return experiences[:6]


def _get_emergency_info(destination: str) -> dict:
    return {
        "emergency_number": "112 (National Emergency)",
        "police": "100",
        "ambulance": "108",
        "fire": "101",
        "tourist_helpline": "1363",
        "nearest_hospital": f"Nearest government hospital in {destination}",
        "tips": [
            "Save hotel address and phone number in your phone.",
            "Keep photocopies of ID and travel documents.",
            "Note the nearest embassy/consulate if travelling internationally.",
            "Download offline maps before travelling to remote areas.",
        ]
    }


def _travel_tips(destination: str, trip_type: str) -> list:
    tips = [
        f"Visit popular spots early morning to avoid crowds in {destination}.",
        "Carry cash for local markets — not all vendors accept cards.",
        "Dress modestly when visiting religious sites.",
        "Always agree on taxi fare before boarding or use app-based cabs.",
        "Stay hydrated and use sunscreen in warm weather.",
        "Buy local SIM card for affordable data roaming.",
    ]
    if trip_type.lower() == "couple":
        tips.append("Book romantic experiences (sunset cruise, candle dinner) in advance.")
    return tips


def _packing_checklist(destination: str, weather: str) -> list:
    checklist = [
        "Valid ID / Passport",
        "Travel insurance documents",
        "Phone charger and power bank",
        "First aid kit (basic medicines)",
        "Sunscreen SPF 50+",
        "Camera / GoPro",
        "Comfortable walking shoes",
        "Reusable water bottle",
        "Snacks for the journey",
    ]
    if "rain" in weather.lower() or "storm" in weather.lower():
        checklist += ["Waterproof jacket", "Umbrella", "Waterproof bag cover"]
    else:
        checklist += ["Light cotton clothes", "Sunglasses", "Hat/Cap"]
    return checklist
