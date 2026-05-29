"""
TransitFlow — Neo4j Graph Database Layer
=========================================
# TASK 6 EXTENSION:
# Adds demonstrable graph-database routing features for fastest routes,
# cheapest routes, station-avoidance alternatives, richer interchange paths,
# and configurable delay-ripple analysis.

This module handles all queries to Neo4j.
"""

from __future__ import annotations

from neo4j import GraphDatabase

from skeleton.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def _driver():
    """Return a Neo4j driver. Caller is responsible for closing."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def example_count_nodes() -> int:
    """Example: count all nodes currently in the graph."""
    with _driver() as driver:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS total")
            return result.single()["total"]


def _relationship_pattern(network: str, origin_id: str = "", destination_id: str = "") -> str:
    """Return the Cypher relationship pattern for the requested network."""
    network = (network or "auto").lower()
    if network == "auto":
        origin = (origin_id or "").upper()
        destination = (destination_id or "").upper()
        if origin.startswith("MS") and destination.startswith("MS"):
            network = "metro"
        elif origin.startswith("NR") and destination.startswith("NR"):
            network = "rail"

    if network == "metro":
        return ":METRO_LINK"
    if network == "rail":
        return ":RAIL_LINK|RAIL_EXPRESS_LINK"
    return ":METRO_LINK|RAIL_LINK|RAIL_EXPRESS_LINK|INTERCHANGE"


def _route_query(weight_expr: str, rel_pattern: str) -> str:
    return f"""
        MATCH (origin:Station {{station_id: $origin_id}})
        MATCH (destination:Station {{station_id: $destination_id}})
        MATCH p = (origin)-[{rel_pattern}*1..12]->(destination)
        WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
        WITH
            p,
            nodes(p) AS ns,
            relationships(p) AS rs,
            reduce(total = 0.0, r IN relationships(p) | total + ({weight_expr})) AS total_weight
        ORDER BY total_weight ASC, length(p) ASC
        LIMIT 1
        RETURN
            total_weight,
            [n IN ns | {{
                station_id: n.station_id,
                name: n.name,
                lines: n.lines
            }}] AS path,
            [i IN range(0, size(rs) - 1) | {{
                from_station_id: ns[i].station_id,
                from_name: ns[i].name,
                to_station_id: ns[i + 1].station_id,
                to_name: ns[i + 1].name,
                connection_type: type(rs[i]),
                line: rs[i].line,
                service_type: rs[i].service_type,
                travel_time_min: coalesce(rs[i].travel_time_min, 0),
                fare_usd: CASE
                    WHEN $fare_class = 'first' THEN coalesce(rs[i].fare_first_usd, rs[i].fare_usd, 0.0)
                    ELSE coalesce(rs[i].fare_standard_usd, rs[i].fare_usd, 0.0)
                END
            }}] AS legs
    """


def _route_from_record(record, origin_id: str, destination_id: str, total_key: str) -> dict:
    if not record:
        return {
            "found": False,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "path": [],
            "legs": [],
        }

    return {
        "found": True,
        "origin_id": origin_id,
        "destination_id": destination_id,
        total_key: round(float(record["total_weight"]), 2),
        "path": record["path"],
        "legs": record["legs"],
    }


def query_shortest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
) -> dict:
    """Find the fastest path between two stations."""
    rel_pattern = _relationship_pattern(network, origin_id, destination_id)

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                _route_query("coalesce(r.travel_time_min, 0)", rel_pattern),
                origin_id=origin_id,
                destination_id=destination_id,
                fare_class="standard",
            )
            record = result.single()

    return _route_from_record(record, origin_id, destination_id, "total_time_min")


def query_cheapest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
    fare_class: str = "standard",
) -> dict:
    """Find the cheapest path between two stations."""
    rel_pattern = _relationship_pattern(network, origin_id, destination_id)
    fare_weight = """
        CASE
            WHEN $fare_class = 'first' THEN coalesce(r.fare_first_usd, r.fare_usd, 0.0)
            ELSE coalesce(r.fare_standard_usd, r.fare_usd, 0.0)
        END
    """

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                _route_query(fare_weight, rel_pattern),
                origin_id=origin_id,
                destination_id=destination_id,
                fare_class=fare_class,
            )
            record = result.single()

    route = _route_from_record(record, origin_id, destination_id, "total_fare_usd")
    if route.get("found"):
        route["fare_class"] = fare_class
        route["note"] = "Fare is estimated from graph edge costs; booking fare remains the source of truth."
    return route


def query_alternative_routes(
    origin_id: str,
    destination_id: str,
    avoid_station_id: str,
    network: str = "auto",
    max_routes: int = 3,
) -> list[list[dict]]:
    """Find routes between two stations that avoid a specific station."""
    rel_pattern = _relationship_pattern(network, origin_id, destination_id)

    query = f"""
        MATCH (origin:Station {{station_id: $origin_id}})
        MATCH (destination:Station {{station_id: $destination_id}})
        MATCH p = (origin)-[{rel_pattern}*1..12]->(destination)
        WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
          AND none(n IN nodes(p)[1..-1] WHERE n.station_id = $avoid_station_id)
        WITH
            p,
            nodes(p) AS ns,
            relationships(p) AS rs,
            reduce(total = 0, r IN relationships(p) | total + coalesce(r.travel_time_min, 0)) AS total_time_min
        ORDER BY total_time_min ASC, length(p) ASC
        LIMIT $max_routes
        RETURN
            total_time_min,
            [i IN range(0, size(rs) - 1) | {{
                from_station_id: ns[i].station_id,
                from_name: ns[i].name,
                to_station_id: ns[i + 1].station_id,
                to_name: ns[i + 1].name,
                connection_type: type(rs[i]),
                line: rs[i].line,
                service_type: rs[i].service_type,
                travel_time_min: coalesce(rs[i].travel_time_min, 0)
            }}] AS legs
    """

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                query,
                origin_id=origin_id,
                destination_id=destination_id,
                avoid_station_id=avoid_station_id,
                max_routes=max_routes,
            )
            return [
                [
                    {
                        **dict(leg),
                        "route_total_time_min": record["total_time_min"],
                    }
                    for leg in record["legs"]
                ]
                for record in result
            ]


def query_interchange_path(origin_id: str, destination_id: str) -> dict:
    """Find a cross-network metro/rail path."""
    rel_pattern = _relationship_pattern("auto")

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                _route_query("coalesce(r.travel_time_min, 0)", rel_pattern),
                origin_id=origin_id,
                destination_id=destination_id,
                fare_class="standard",
            )
            record = result.single()

    route = _route_from_record(record, origin_id, destination_id, "total_time_min")
    if not route.get("found"):
        return route

    route["stations"] = [station["station_id"] for station in route["path"]]
    route["interchange_points"] = [
        {
            "from_station_id": leg["from_station_id"],
            "from_name": leg["from_name"],
            "to_station_id": leg["to_station_id"],
            "to_name": leg["to_name"],
        }
        for leg in route["legs"]
        if leg["connection_type"] == "INTERCHANGE"
    ]
    return route


def query_delay_ripple(delayed_station_id: str, hops: int = 2) -> list[dict]:
    """Find all stations within N hops of a delayed or disrupted station."""
    hops = max(1, min(int(hops), 6))

    with _driver() as driver:
        with driver.session() as session:
            result = session.run(
                f"""
                MATCH (start:Station {{station_id:$delayed_station_id}})
                MATCH p = (start)-[*1..{hops}]-(affected:Station)
                WHERE affected.station_id <> $delayed_station_id
                WITH affected, min(length(p)) AS hops_away
                RETURN
                    affected.station_id AS station_id,
                    affected.name AS name,
                    hops_away,
                    affected.lines AS lines_affected
                ORDER BY hops_away, station_id
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
                station_id=station_id,
            )

            return [
                {
                    "station_id": record["station_id"],
                    "name": record["name"],
                    "connection_type": record["connection_type"],
                    "travel_time_min": record["travel_time_min"],
                }
                for record in result
            ]
