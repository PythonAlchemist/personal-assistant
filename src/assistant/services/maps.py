"""Google Maps integration — directions, places, distances, geocoding."""

from __future__ import annotations

from datetime import datetime

from assistant import config


def _get_client():
    import googlemaps

    if not config.GOOGLE_MAPS_API_KEY:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY not set. Add it to data/.env or set the environment variable."
        )
    return googlemaps.Client(key=config.GOOGLE_MAPS_API_KEY)


def directions(
    origin: str,
    destination: str,
    mode: str = "driving",
    departure_time: datetime | None = None,
    alternatives: bool = True,
) -> list[dict]:
    """Get directions between two places. Returns route summaries."""
    client = _get_client()
    result = client.directions(
        origin, destination, mode=mode,
        departure_time=departure_time or "now",
        alternatives=alternatives,
    )
    routes = []
    for route in result:
        leg = route["legs"][0]
        routes.append({
            "summary": route.get("summary", ""),
            "distance": leg["distance"]["text"],
            "duration": leg["duration"]["text"],
            "duration_in_traffic": leg.get("duration_in_traffic", {}).get("text", ""),
            "start_address": leg.get("start_address", ""),
            "end_address": leg.get("end_address", ""),
            "steps": [
                {"instruction": s.get("html_instructions", ""), "distance": s["distance"]["text"],
                 "duration": s["duration"]["text"]}
                for s in leg.get("steps", [])
            ],
        })
    return routes


def distance_matrix(
    origins: list[str],
    destinations: list[str],
    mode: str = "driving",
    departure_time: datetime | None = None,
) -> list[dict]:
    """Get travel times/distances between multiple origins and destinations."""
    client = _get_client()
    result = client.distance_matrix(
        origins, destinations, mode=mode,
        departure_time=departure_time or "now",
    )
    rows = []
    for i, row in enumerate(result.get("rows", [])):
        for j, element in enumerate(row.get("elements", [])):
            if element["status"] == "OK":
                rows.append({
                    "origin": result["origin_addresses"][i],
                    "destination": result["destination_addresses"][j],
                    "distance": element["distance"]["text"],
                    "duration": element["duration"]["text"],
                    "duration_in_traffic": element.get("duration_in_traffic", {}).get("text", ""),
                })
    return rows


def search_places(
    query: str,
    location: str | None = None,
    radius: int = 5000,
    type: str | None = None,
) -> list[dict]:
    """Search for places. Location can be an address or 'lat,lng'."""
    client = _get_client()

    kwargs = {"query": query, "radius": radius}
    if location:
        geo = geocode(location)
        if geo:
            kwargs["location"] = (geo[0]["lat"], geo[0]["lng"])
    if type:
        kwargs["type"] = type

    result = client.places(**kwargs)
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("formatted_address", ""),
            "rating": p.get("rating", ""),
            "total_ratings": p.get("user_ratings_total", 0),
            "price_level": p.get("price_level", ""),
            "open_now": p.get("opening_hours", {}).get("open_now"),
            "place_id": p.get("place_id", ""),
            "types": p.get("types", []),
        }
        for p in result.get("results", [])
    ]


def place_details(place_id: str) -> dict:
    """Get detailed info about a place."""
    client = _get_client()
    result = client.place(
        place_id,
        fields=[
            "name", "formatted_address", "formatted_phone_number",
            "website", "rating", "user_ratings_total", "price_level",
            "opening_hours", "reviews", "geometry",
        ],
    )
    p = result.get("result", {})
    hours = p.get("opening_hours", {})
    return {
        "name": p.get("name", ""),
        "address": p.get("formatted_address", ""),
        "phone": p.get("formatted_phone_number", ""),
        "website": p.get("website", ""),
        "rating": p.get("rating", ""),
        "total_ratings": p.get("user_ratings_total", 0),
        "price_level": p.get("price_level", ""),
        "hours": hours.get("weekday_text", []),
        "open_now": hours.get("open_now"),
        "reviews": [
            {"author": r.get("author_name", ""), "rating": r.get("rating", ""),
             "text": r.get("text", ""), "time": r.get("relative_time_description", "")}
            for r in p.get("reviews", [])[:5]
        ],
    }


def nearby_places(
    location: str,
    radius: int = 5000,
    type: str | None = None,
    keyword: str | None = None,
) -> list[dict]:
    """Find places near a location. Useful for 'things to do nearby'."""
    client = _get_client()
    geo = geocode(location)
    if not geo:
        return []

    kwargs = {
        "location": (geo[0]["lat"], geo[0]["lng"]),
        "radius": radius,
    }
    if type:
        kwargs["type"] = type
    if keyword:
        kwargs["keyword"] = keyword

    result = client.places_nearby(**kwargs)
    return [
        {
            "name": p.get("name", ""),
            "address": p.get("vicinity", ""),
            "rating": p.get("rating", ""),
            "total_ratings": p.get("user_ratings_total", 0),
            "open_now": p.get("opening_hours", {}).get("open_now"),
            "place_id": p.get("place_id", ""),
            "types": p.get("types", []),
        }
        for p in result.get("results", [])
    ]


def geocode(address: str) -> list[dict]:
    """Convert an address to coordinates."""
    client = _get_client()
    result = client.geocode(address)
    return [
        {
            "address": r.get("formatted_address", ""),
            "lat": r["geometry"]["location"]["lat"],
            "lng": r["geometry"]["location"]["lng"],
        }
        for r in result
    ]


def reverse_geocode(lat: float, lng: float) -> list[dict]:
    """Convert coordinates to addresses."""
    client = _get_client()
    result = client.reverse_geocode((lat, lng))
    return [
        {"address": r.get("formatted_address", ""), "types": r.get("types", [])}
        for r in result[:3]
    ]
