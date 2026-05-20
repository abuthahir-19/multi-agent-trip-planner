"""Budget tool — cost estimation, optimization, and currency conversion."""


def calculate_budget(trip_preferences: dict, transport_data: dict,
                     hotel_data: dict) -> dict:
    """Estimate total trip cost and optimize within the user's budget."""

    prefs = trip_preferences
    total_budget = float(prefs.get("budget", 30000))
    num_travelers = int(prefs.get("num_travelers", 2))
    num_days = int(prefs.get("num_days", 5))

    transport_cost = _extract_transport_cost(transport_data, num_travelers)
    hotel_cost = _extract_hotel_cost(hotel_data, num_days)
    food_cost = _estimate_food_cost(prefs, num_travelers, num_days)
    sightseeing_cost = _estimate_sightseeing_cost(num_travelers, num_days)
    misc_cost = _estimate_misc_cost(num_travelers, num_days)

    total_estimated = transport_cost + hotel_cost + food_cost + sightseeing_cost + misc_cost
    budget_per_person = total_budget / num_travelers
    estimated_per_person = total_estimated / num_travelers

    over_budget = total_estimated > total_budget
    savings = total_budget - total_estimated

    breakdown = {
        "transport": {"total": round(transport_cost), "per_person": round(transport_cost / num_travelers)},
        "accommodation": {"total": round(hotel_cost), "per_person": round(hotel_cost / num_travelers)},
        "food": {"total": round(food_cost), "per_person": round(food_cost / num_travelers)},
        "sightseeing": {"total": round(sightseeing_cost), "per_person": round(sightseeing_cost / num_travelers)},
        "miscellaneous": {"total": round(misc_cost), "per_person": round(misc_cost / num_travelers)},
    }

    result = {
        "total_budget": round(total_budget),
        "total_estimated": round(total_estimated),
        "budget_per_person": round(budget_per_person),
        "estimated_per_person": round(estimated_per_person),
        "savings_or_deficit": round(savings),
        "over_budget": over_budget,
        "breakdown": breakdown,
        "percentages": _calculate_percentages(breakdown, total_estimated),
        "optimization_tips": _get_optimization_tips(breakdown, total_budget, over_budget, prefs),
        "currency": "INR (₹)",
    }

    if over_budget:
        result["budget_alert"] = (
            f"Estimated cost ₹{total_estimated:,.0f} exceeds budget ₹{total_budget:,.0f} "
            f"by ₹{abs(savings):,.0f}. See optimization tips."
        )
    else:
        result["budget_status"] = (
            f"Trip fits within budget! You'll have ₹{savings:,.0f} to spare."
        )

    return result


def _extract_transport_cost(transport_data: dict, pax: int) -> float:
    if not transport_data:
        return pax * 3000
    flights = transport_data.get("flights", [])
    trains = transport_data.get("trains", [])
    if flights:
        cheapest = min(flights, key=lambda x: x.get("price_per_person", 9999))
        return cheapest.get("price_per_person", 3000) * pax
    if trains:
        return trains[0].get("price_per_person", 800) * pax
    return pax * 2000


def _extract_hotel_cost(hotel_data: dict, num_days: int) -> float:
    if not hotel_data:
        return num_days * 3000
    recommended = hotel_data.get("recommended", {})
    if recommended:
        return recommended.get("price_per_night", 3000) * num_days
    hotels = hotel_data.get("hotels", [])
    if hotels:
        return hotels[0].get("price_per_night", 3000) * num_days
    return num_days * 3000


def _estimate_food_cost(prefs: dict, pax: int, days: int) -> float:
    pref = prefs.get("food_preference", "").lower()
    if "luxury" in pref or "fine dining" in pref:
        daily_pp = 2000
    elif "budget" in pref or "street" in pref:
        daily_pp = 400
    else:
        daily_pp = 800
    return daily_pp * pax * days


def _estimate_sightseeing_cost(pax: int, days: int) -> float:
    return pax * days * 500


def _estimate_misc_cost(pax: int, days: int) -> float:
    return pax * days * 300


def _calculate_percentages(breakdown: dict, total: float) -> dict:
    if total == 0:
        return {}
    return {k: round(v["total"] / total * 100, 1) for k, v in breakdown.items()}


def _get_optimization_tips(breakdown: dict, budget: float, over_budget: bool,
                            prefs: dict) -> list:
    tips = []
    b = breakdown

    if over_budget:
        tips.append("You are over budget. Consider the following adjustments:")

    if b["accommodation"]["total"] > budget * 0.4:
        tips.append("Hotel cost is high (>40% of budget). Consider a 3-star property or book early for deals.")

    if b["transport"]["total"] > budget * 0.35:
        tips.append("Transport cost is high. Consider train instead of flight, or travel during off-peak hours.")

    if b["food"]["total"] > budget * 0.25:
        tips.append("Reduce dining cost: try local dhabas/street food instead of restaurants for 1-2 meals/day.")

    tips += [
        "Use cashback apps like Cred or Google Pay for hotel/flight bookings.",
        "Book combo packages (flight+hotel) on MakeMyTrip or Goibibo for savings.",
        "Travel on weekdays — flights and hotels are cheaper mid-week.",
        "Carry snacks from home to reduce per-day food expenses.",
        "Use public transport (bus/metro) for city sightseeing instead of cabs.",
    ]

    return tips[:6]
