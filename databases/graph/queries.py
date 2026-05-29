"""
TransitFlow — Neo4j Graph Database Layer
=========================================
This module handles all queries to Neo4j.

GRAPH ROLE:
  - Model the dual transit network (city metro M1–M4 + national rail NR1–NR2)
  - Find fastest routes (Dijkstra by travel_time_min via APOC)
  - Find cheapest routes (Dijkstra by fare via APOC)
  - Find alternative routes avoiding a given station
  - Find cross-network interchange paths (metro → rail or rail → metro)
  - Show delay ripple: which stations are affected within N hops

STUDENT TASK
------------
Design your graph schema (node labels, relationship types, properties)
based on the data in train-mock-data/, seed it with skeleton/seed_neo4j.py,
then implement the query_ functions below.

Functions prefixed with `query_` are called by the agent (skeleton/agent.py).
"""

from __future__ import annotations

from typing import Optional

from neo4j import GraphDatabase

from skeleton.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def _driver():
    """Return a Neo4j driver. Caller is responsible for closing."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# ── Example ───────────────────────────────────────────────────────────────────
# The block below shows the query pattern: open a session, run Cypher, return data.

def example_count_nodes() -> int:
    """Example: count all nodes currently in the graph."""
    with _driver() as driver:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS total")
            return result.single()["total"]

# TODO: Implement the query_ functions below.
# ─────────────────────────────────────────────────────────────────────────────


# ── FASTEST ROUTE (Dijkstra by travel_time_min) ───────────────────────────────

def query_shortest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
) -> dict:
    """
    Find the fastest path between two stations, minimising total travel time.
    Uses apoc.algo.dijkstra (APOC required; enabled in docker-compose.yml).

    Args:
        origin_id:       e.g. "MS01" or "NR01"
        destination_id:  e.g. "MS09" or "NR05"
        network:         "metro", "rail", or "auto" (inferred from IDs)

    Returns:
        dict with keys: found, origin_id, destination_id,
                        total_time_min, path (list of station dicts), legs
    """
    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH p = shortestPath(
                    (a:Station {station_id:$origin_id})-[*]-(b:Station {station_id:$destination_id})
                )
                RETURN
                    [x IN nodes(p) | {
                        station_id: x.station_id,
                        name: x.name,
                        labels: labels(x),
                        lines: x.lines
                    }] AS path,
                    [r IN relationships(p) | {
                        type: type(r),
                        line: r.line,
                        travel_time_min: coalesce(r.travel_time_min, 0)
                    }] AS legs,
                    reduce(total = 0,
                        r IN relationships(p) |
                        total + coalesce(r.travel_time_min, 0)
                    ) AS total_time_min
                """,
                origin_id=origin_id,
                destination_id=destination_id
            )

            record = result.single()

            if not record:
                return {
                    "found": False,
                    "origin_id": origin_id,
                    "destination_id": destination_id,
                    "total_time_min": None,
                    "path": [],
                    "legs": []
                }

            return {
                "found": True,
                "origin_id": origin_id,
                "destination_id": destination_id,
                "total_time_min": record["total_time_min"],
                "path": record["path"],
                "legs": record["legs"]
            }

# ── CHEAPEST ROUTE (Dijkstra by fare) ────────────────────────────────────────

def query_cheapest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
    fare_class: str = "standard",
) -> dict:
    """
    Find the cheapest path between two stations, minimising total estimated fare.

    Args:
        origin_id:       e.g. "NR01"
        destination_id:  e.g. "NR05"
        network:         "metro", "rail", or "auto"
        fare_class:      "standard" or "first" (national rail only)

    Returns:
        dict with found, total_fare_usd (approximate), stations, legs
    """
    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH p = (a:Station {station_id:$origin_id})-[*1..10]-(b:Station {station_id:$destination_id})
                WITH p,
                     reduce(total = 0.0,
                         r IN relationships(p) |
                         total +
                         CASE
                             WHEN type(r) = 'METRO_LINK' THEN 1.50
                             WHEN type(r) = 'RAIL_LINK' AND $fare_class = 'first' THEN coalesce(r.travel_time_min, 0) * 0.45
                             WHEN type(r) = 'RAIL_LINK' THEN coalesce(r.travel_time_min, 0) * 0.30
                             WHEN type(r) = 'INTERCHANGE' THEN 0.00
                             ELSE 0.00
                         END
                     ) AS total_fare_usd,
                     reduce(total = 0,
                         r IN relationships(p) |
                         total + coalesce(r.travel_time_min, 0)
                     ) AS total_time_min
                RETURN
                    [x IN nodes(p) | {
                        station_id: x.station_id,
                        name: x.name,
                        labels: labels(x),
                        lines: x.lines
                    }] AS stations,
                    [r IN relationships(p) | {
                        type: type(r),
                        line: r.line,
                        travel_time_min: coalesce(r.travel_time_min, 0)
                    }] AS legs,
                    total_fare_usd,
                    total_time_min
                ORDER BY total_fare_usd ASC, total_time_min ASC
                LIMIT 1
                """,
                origin_id=origin_id,
                destination_id=destination_id,
                fare_class=fare_class
            )

            record = result.single()

            if not record:
                return {
                    "found": False,
                    "origin_id": origin_id,
                    "destination_id": destination_id,
                    "total_fare_usd": None,
                    "total_time_min": None,
                    "stations": [],
                    "legs": []
                }

            return {
                "found": True,
                "origin_id": origin_id,
                "destination_id": destination_id,
                "fare_class": fare_class,
                "total_fare_usd": round(record["total_fare_usd"], 2),
                "total_time_min": record["total_time_min"],
                "stations": record["stations"],
                "legs": record["legs"]
            }


# ── ALTERNATIVE ROUTES (avoiding a station) ───────────────────────────────────

def query_alternative_routes(
    origin_id: str,
    destination_id: str,
    avoid_station_id: str,
    network: str = "auto",
    max_routes: int = 3,
) -> list[list[dict]]:
    """
    Find paths between two stations that avoid a specific intermediate station.
    Useful for routing around a delayed or closed station.

    Args:
        origin_id:         e.g. "NR01"
        destination_id:    e.g. "NR05"
        avoid_station_id:  e.g. "NR03"
        network:           "metro", "rail", or "auto"
        max_routes:        max number of alternatives to return

    Returns:
        List of routes, each route is a list of leg dicts
    """
    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH p = (a:Station {station_id:$origin_id})-[*1..10]-(b:Station {station_id:$destination_id})
                WHERE NONE(x IN nodes(p) WHERE x.station_id = $avoid_station_id)
                WITH p,
                     reduce(total = 0,
                         r IN relationships(p) |
                         total + coalesce(r.travel_time_min, 0)
                     ) AS total_time_min
                RETURN
                    [x IN nodes(p) | {
                        station_id: x.station_id,
                        name: x.name,
                        labels: labels(x),
                        lines: x.lines
                    }] AS stations,
                    [r IN relationships(p) | {
                        type: type(r),
                        line: r.line,
                        travel_time_min: coalesce(r.travel_time_min, 0)
                    }] AS legs,
                    total_time_min
                ORDER BY total_time_min ASC
                LIMIT $max_routes
                """,
                origin_id=origin_id,
                destination_id=destination_id,
                avoid_station_id=avoid_station_id,
                max_routes=max_routes
            )

            return [
                {
                    "found": True,
                    "origin_id": origin_id,
                    "destination_id": destination_id,
                    "avoid_station_id": avoid_station_id,
                    "total_time_min": record["total_time_min"],
                    "stations": record["stations"],
                    "legs": record["legs"]
                }
                for record in result
            ]


# ── CROSS-NETWORK INTERCHANGE PATH ───────────────────────────────────────────

def query_interchange_path(origin_id: str, destination_id: str) -> dict:
    """
    Find a path between a metro station and a national rail station (or vice versa)
    crossing the network boundary via interchange relationships.

    Args:
        origin_id:       e.g. "MS03" (metro) or "NR05" (national rail)
        destination_id:  e.g. "NR05" (national rail) or "MS09" (metro)

    Returns:
        dict with found, stations list, interchange points, total_time_min
    """
    with _driver() as driver:
        with driver.session() as session:

            result = session.run(
                """
                MATCH p = shortestPath(
                    (a:Station {station_id:$origin_id})-[*]-(b:Station {station_id:$destination_id})
                )

                RETURN
                    [x IN nodes(p) | x.station_id] AS stations,
                    reduce(total = 0,
                           r IN relationships(p) |
                           total + coalesce(r.travel_time_min, 0)
                    ) AS total_time_min
                """,
                origin_id=origin_id,
                destination_id=destination_id
            )

            record = result.single()

            if not record:
                return {
                    "found": False
                }

            interchange_points = [
                s for s in record["stations"]
                if s.startswith("MS") or s.startswith("NR")
            ]

            return {
                "found": True,
                "stations": record["stations"],
                "interchange_points": interchange_points,
                "total_time_min": record["total_time_min"]
            }


# ── DELAY RIPPLE ANALYSIS ─────────────────────────────────────────────────────

def query_delay_ripple(delayed_station_id: str, hops: int = 2) -> list[dict]:
    """
    Find all stations within N hops of a delayed or disrupted station.
    Works on both metro and national rail networks.
    """
    if hops == 0:
        with _driver() as driver:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (s:Station {station_id:$delayed_station_id})
                    RETURN
                        s.station_id AS station_id,
                        s.name AS name,
                        0 AS hops_away,
                        s.lines AS lines_affected
                    """,
                    delayed_station_id=delayed_station_id,
                )

                return [
                    {
                        "station_id": record["station_id"],
                        "name": record["name"],
                        "hops_away": record["hops_away"],
                        "lines_affected": record["lines_affected"],
                    }
                    for record in result
                ]

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (start:Station {station_id:$delayed_station_id})
                MATCH p = (start)-[*1..10]-(affected:Station)
                WHERE affected.station_id <> $delayed_station_id
                  AND length(p) <= $hops
                RETURN DISTINCT
                    affected.station_id AS station_id,
                    affected.name AS name,
                    length(p) AS hops_away,
                    affected.lines AS lines_affected
                ORDER BY hops_away, station_id
                """,
                delayed_station_id=delayed_station_id,
                hops=hops,
            )

            return [
                {
                    "station_id": record["station_id"],
                    "name": record["name"],
                    "hops_away": record["hops_away"],
                    "lines_affected": record["lines_affected"],
                }
                for record in result
            ]
# ── STATION CONNECTIONS ───────────────────────────────────────────────────────

def query_station_connections(station_id: str) -> list[dict]:
    with _driver() as driver:
        with driver.session() as session:

            result = session.run(
                """
                MATCH (s:Station {station_id:$station_id})-[r]-(connected:Station)

                RETURN DISTINCT
                    connected.station_id AS station_id,
                    connected.name AS name,
                    type(r) AS connection_type,
                    r.travel_time_min AS travel_time_min
                ORDER BY connected.station_id
                """,
                station_id=station_id
            )

            return [
                {
                    "station_id": record["station_id"],
                    "name": record["name"],
                    "connection_type": record["connection_type"],
                    "travel_time_min": record["travel_time_min"]
                }
                for record in result
            ]