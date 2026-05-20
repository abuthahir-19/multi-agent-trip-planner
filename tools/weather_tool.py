"""Weather tool — uses OpenWeatherMap API; falls back to simulated data."""
import requests
from config.settings import OPENWEATHER_API_KEY


def get_weather_forecast(city: str, travel_dates: str = "") -> dict:
    """Fetch 5-day weather forecast for the destination city."""
    if OPENWEATHER_API_KEY:
        return _fetch_from_api(city, travel_dates)
    return _simulated_weather(city, travel_dates)


def _fetch_from_api(city: str, travel_dates: str) -> dict:
    base_url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric", "cnt": 40}
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        forecasts = []
        seen_dates = set()
        for item in data.get("list", []):
            date = item["dt_txt"].split(" ")[0]
            if date not in seen_dates:
                seen_dates.add(date)
                forecasts.append({
                    "date": date,
                    "temp_min": item["main"]["temp_min"],
                    "temp_max": item["main"]["temp_max"],
                    "description": item["weather"][0]["description"],
                    "humidity": item["main"]["humidity"],
                    "wind_speed": item["wind"]["speed"],
                })
        city_info = data.get("city", {})
        return {
            "source": "OpenWeatherMap API",
            "city": city_info.get("name", city),
            "country": city_info.get("country", ""),
            "travel_dates": travel_dates,
            "forecasts": forecasts[:7],
            "summary": _summarize_weather(forecasts),
            "travel_advisory": _travel_advisory(forecasts),
        }
    except Exception as e:
        return _simulated_weather(city, travel_dates, error=str(e))


def _simulated_weather(city: str, travel_dates: str, error: str = "") -> dict:
    """Return realistic simulated weather when API key is unavailable."""
    city_lower = city.lower()

    beach_cities = ["goa", "phuket", "bali", "maldives", "miami", "cancun"]
    mountain_cities = ["shimla", "manali", "darjeeling", "leh", "ooty", "munnar"]
    desert_cities = ["jaisalmer", "dubai", "rajasthan", "jaipur"]

    if any(c in city_lower for c in beach_cities):
        base_temp, desc = 30, "partly cloudy with sea breeze"
    elif any(c in city_lower for c in mountain_cities):
        base_temp, desc = 15, "cool and pleasant with clear skies"
    elif any(c in city_lower for c in desert_cities):
        base_temp, desc = 35, "sunny and dry"
    else:
        base_temp, desc = 28, "warm and pleasant"

    import datetime
    today = datetime.date.today()
    forecasts = []
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        forecasts.append({
            "date": str(d),
            "temp_min": base_temp - 5,
            "temp_max": base_temp + 3,
            "description": desc,
            "humidity": 65,
            "wind_speed": 12,
        })

    result = {
        "source": "Simulated Data (set OPENWEATHER_API_KEY for live data)",
        "city": city,
        "country": "IN",
        "travel_dates": travel_dates,
        "forecasts": forecasts,
        "summary": f"Expected weather in {city}: {desc}, {base_temp-5}°C – {base_temp+3}°C",
        "travel_advisory": _travel_advisory(forecasts),
    }
    if error:
        result["api_error"] = error
    return result


def _summarize_weather(forecasts: list) -> str:
    if not forecasts:
        return "No forecast data available."
    avg_max = sum(f["temp_max"] for f in forecasts) / len(forecasts)
    descriptions = [f["description"] for f in forecasts]
    most_common = max(set(descriptions), key=descriptions.count)
    return f"Average high: {avg_max:.1f}°C. Predominant condition: {most_common}."


def _travel_advisory(forecasts: list) -> str:
    if not forecasts:
        return "No advisory available."
    heavy_rain = any("heavy rain" in f.get("description", "") for f in forecasts)
    storm = any("storm" in f.get("description", "") or "thunder" in f.get("description", "") for f in forecasts)
    avg_temp = sum(f.get("temp_max", 30) for f in forecasts) / max(len(forecasts), 1)

    advisories = []
    if storm:
        advisories.append("Thunderstorms expected — carry rain gear and plan indoor alternatives.")
    elif heavy_rain:
        advisories.append("Heavy rain forecast — pack waterproof clothing.")
    if avg_temp > 35:
        advisories.append("High temperatures expected — stay hydrated and avoid midday sun.")
    elif avg_temp < 10:
        advisories.append("Cold weather expected — pack warm layers.")
    if not advisories:
        advisories.append("Weather looks favorable for travel. Carry light layers for evenings.")
    return " ".join(advisories)
