"""Google Maps CLI commands."""

from __future__ import annotations

import re

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from assistant.services import maps as maps_svc

console = Console()


def _handle_maps_error(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            console.print(f"[red]Maps error: {e}[/red]")
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@click.group()
def maps():
    """Google Maps — directions, places, distances."""
    pass


@maps.command()
@click.argument("origin")
@click.argument("destination")
@click.option("--mode", "-m", type=click.Choice(["driving", "walking", "bicycling", "transit"]), default="driving")
@_handle_maps_error
def directions(origin: str, destination: str, mode: str):
    """Get directions between two places."""
    routes = maps_svc.directions(origin, destination, mode=mode)
    if not routes:
        console.print("[dim]No routes found.[/dim]")
        return

    for i, route in enumerate(routes):
        traffic = f" (in traffic: {route['duration_in_traffic']})" if route["duration_in_traffic"] else ""
        title = f"Route {i + 1}: {route['summary']}" if route["summary"] else f"Route {i + 1}"
        header = f"[bold]{route['distance']}[/bold] — {route['duration']}{traffic}"
        console.print(Panel(header, title=title, border_style="blue"))

        for step in route["steps"]:
            instruction = re.sub(r"<[^>]+>", "", step["instruction"])
            console.print(f"  {instruction} ({step['distance']})")
        console.print()


@maps.command()
@click.argument("origin")
@click.argument("destinations", nargs=-1, required=True)
@click.option("--mode", "-m", type=click.Choice(["driving", "walking", "bicycling", "transit"]), default="driving")
@_handle_maps_error
def distance(origin: str, destinations: tuple, mode: str):
    """Get distance/time from origin to one or more destinations."""
    results = maps_svc.distance_matrix([origin], list(destinations), mode=mode)
    if not results:
        console.print("[dim]No results.[/dim]")
        return

    table = Table(title=f"From: {origin}")
    table.add_column("Destination", style="bold")
    table.add_column("Distance")
    table.add_column("Duration")
    table.add_column("In Traffic", style="dim")
    for r in results:
        table.add_row(r["destination"], r["distance"], r["duration"], r.get("duration_in_traffic", ""))
    console.print(table)


@maps.command()
@click.argument("query")
@click.option("--near", "-n", default=None, help="Search near this location")
@click.option("--radius", "-r", default=5000, help="Search radius in meters")
@click.option("--type", "-t", "place_type", default=None, help="Place type filter (restaurant, park, etc.)")
@_handle_maps_error
def search(query: str, near: str | None, radius: int, place_type: str | None):
    """Search for places."""
    results = maps_svc.search_places(query, location=near, radius=radius, type=place_type)
    if not results:
        console.print("[dim]No places found.[/dim]")
        return

    table = Table(title=f"Places: {query}")
    table.add_column("Name", style="bold")
    table.add_column("Rating", justify="center")
    table.add_column("Address")
    table.add_column("Open", justify="center")
    for p in results:
        rating = f"{p['rating']} ({p['total_ratings']})" if p["rating"] else "—"
        open_now = "Yes" if p.get("open_now") is True else ("No" if p.get("open_now") is False else "—")
        table.add_row(p["name"], rating, p["address"], open_now)
    console.print(table)


@maps.command()
@click.argument("location")
@click.option("--radius", "-r", default=5000, help="Search radius in meters")
@click.option("--type", "-t", "place_type", default=None, help="Place type (park, restaurant, museum, etc.)")
@click.option("--keyword", "-k", default=None, help="Keyword filter")
@_handle_maps_error
def nearby(location: str, radius: int, place_type: str | None, keyword: str | None):
    """Find places near a location."""
    results = maps_svc.nearby_places(location, radius=radius, type=place_type, keyword=keyword)
    if not results:
        console.print("[dim]No places found nearby.[/dim]")
        return

    table = Table(title=f"Near: {location}")
    table.add_column("Name", style="bold")
    table.add_column("Rating", justify="center")
    table.add_column("Address")
    table.add_column("Open", justify="center")
    for p in results:
        rating = f"{p['rating']} ({p['total_ratings']})" if p["rating"] else "—"
        open_now = "Yes" if p.get("open_now") is True else ("No" if p.get("open_now") is False else "—")
        table.add_row(p["name"], rating, p["address"], open_now)
    console.print(table)


@maps.command()
@click.argument("place_query")
@_handle_maps_error
def details(place_query: str):
    """Get detailed info about a place (search by name first)."""
    places = maps_svc.search_places(place_query)
    if not places:
        console.print("[dim]No places found.[/dim]")
        return

    place = places[0]
    info = maps_svc.place_details(place["place_id"])

    lines = [f"[bold]{info['name']}[/bold]"]
    lines.append(f"Address: {info['address']}")
    if info["phone"]:
        lines.append(f"Phone: {info['phone']}")
    if info["website"]:
        lines.append(f"Web: {info['website']}")
    if info["rating"]:
        lines.append(f"Rating: {info['rating']} ({info['total_ratings']} reviews)")
    if info["hours"]:
        lines.append("\nHours:")
        for h in info["hours"]:
            lines.append(f"  {h}")
    console.print(Panel("\n".join(lines), border_style="blue"))

    if info["reviews"]:
        console.print("\n[bold]Recent Reviews:[/bold]")
        for r in info["reviews"]:
            stars = "★" * int(r["rating"]) + "☆" * (5 - int(r["rating"]))
            console.print(f"  {stars} — {r['author']} ({r['time']})")
            if r["text"]:
                console.print(f"    {r['text'][:200]}")
