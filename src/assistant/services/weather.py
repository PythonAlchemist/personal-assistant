"""Weather via Open-Meteo API (free, no key required)."""

from __future__ import annotations

import json
import urllib.request
from datetime import date

# Harrisburg, NC
DEFAULT_LAT = 35.2271
DEFAULT_LON = -80.6490
DEFAULT_LOCATION = "Harrisburg, NC"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ slight hail", 99: "Thunderstorm w/ heavy hail",
}


def get_current_and_forecast(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
) -> dict:
    """Get current weather and 7-day forecast."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"weather_code,wind_speed_10m,precipitation"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        f"precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
        f"&precipitation_unit=inch&timezone=America%2FNew_York"
    )

    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())

    current = data.get("current", {})
    daily = data.get("daily", {})

    result = {
        "location": DEFAULT_LOCATION,
        "current": {
            "temp": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
            "condition": WMO_CODES.get(current.get("weather_code", -1), "Unknown"),
        },
        "forecast": [],
    }

    dates = daily.get("time", [])
    for i, d in enumerate(dates):
        result["forecast"].append({
            "date": d,
            "high": daily["temperature_2m_max"][i],
            "low": daily["temperature_2m_min"][i],
            "condition": WMO_CODES.get(daily["weather_code"][i], "Unknown"),
            "precip_chance": daily["precipitation_probability_max"][i],
            "precip_amount": daily["precipitation_sum"][i],
            "wind_max": daily["wind_speed_10m_max"][i],
        })

    return result


def get_today_summary(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict:
    """Get just today's weather summary for the briefing."""
    data = get_current_and_forecast(lat, lon)
    today_forecast = data["forecast"][0] if data["forecast"] else {}
    return {
        "location": data["location"],
        "current": data["current"],
        "today": today_forecast,
        "tomorrow": data["forecast"][1] if len(data["forecast"]) > 1 else {},
    }
