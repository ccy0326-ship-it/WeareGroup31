"""
TransitFlow — Neo4j Seeder
# TASK 6 EXTENSION:
# Seeds extra graph relationship properties used by the extension queries:
# metro fares, rail fare classes, express rail links, and interchange costs.

Run once after starting Docker:
    python skeleton/seed_neo4j.py

Loads station and network data from train-mock-data/:
  - metro_stations.json         — city metro stations and adjacencies
  - national_rail_stations.json — national rail stations and adjacencies

Design your graph schema (node labels, relationship types, properties)
based on the data in these files, then implement the seed() function below.
"""

import json
import os
import sys

sys.path.insert(0, ".")

from neo4j import GraphDatabase
from skeleton.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "train-mock-data")
)


def _load(filename):
    with open(os.path.join(_DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def seed():
    metro_stations = _load("metro_stations.json")
    metro_schedules = _load("metro_schedules.json")
    rail_stations = _load("national_rail_stations.json")
    rail_schedules = _load("national_rail_schedules.json")

    metro_fare_by_line = {
        schedule["line"]: float(schedule["per_stop_rate_usd"])
        for schedule in metro_schedules
    }
    rail_fare_by_line = {
        schedule["line"]: {
            "standard": float(schedule["fare_classes"]["standard"]["per_stop_rate_usd"]),
            "first": float(schedule["fare_classes"]["first"]["per_stop_rate_usd"]),
        }
        for schedule in rail_schedules
        if schedule["service_type"] == "normal"
    }

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:

        session.run("MATCH (n) DETACH DELETE n")
        print("  Cleared existing graph data")

        # Create metro station nodes
        for s in metro_stations:
            session.run(
                """
                MERGE (m:MetroStation:Station {station_id: $station_id})
                SET m.name = $name,
                    m.lines = $lines
                """,
                station_id=s["station_id"],
                name=s["name"],
                lines=s["lines"],
            )

        # Create metro route relationships
        for s in metro_stations:
            for adj in s["adjacent_stations"]:
                session.run(
                    """
                    MATCH (a:MetroStation {station_id: $from_id})
                    MATCH (b:MetroStation {station_id: $to_id})
                    MERGE (a)-[r:METRO_LINK]->(b)
                    SET r.line = $line,
                        r.travel_time_min = $travel_time_min,
                        r.fare_usd = $fare_usd
                    """,
                    from_id=s["station_id"],
                    to_id=adj["station_id"],
                    line=adj["line"],
                    travel_time_min=adj["travel_time_min"],
                    fare_usd=metro_fare_by_line.get(adj["line"], 0.30),
                )
        # Create national rail station nodes
        for s in rail_stations:
            session.run(
                """
                MERGE (r:RailStation:Station {station_id: $station_id})
                SET r.name = $name,
                    r.lines = $lines,
                    r.is_interchange_national_rail = $is_interchange_national_rail,
                    r.interchange_national_rail_lines = $interchange_national_rail_lines,
                    r.is_interchange_metro = $is_interchange_metro,
                    r.interchange_metro_station_id = $interchange_metro_station_id
                """,
                station_id=s["station_id"],
                name=s["name"],
                lines=s["lines"],
                is_interchange_national_rail=s["is_interchange_national_rail"],
                interchange_national_rail_lines=s["interchange_national_rail_lines"],
                is_interchange_metro=s["is_interchange_metro"],
                interchange_metro_station_id=s["interchange_metro_station_id"],
            )

        # Create national rail route relationships
        for s in rail_stations:
            for adj in s["adjacent_stations"]:
                session.run(
                    """
                    MATCH (a:RailStation {station_id: $from_id})
                    MATCH (b:RailStation {station_id: $to_id})
                    MERGE (a)-[r:RAIL_LINK]->(b)
                    SET r.line = $line,
                        r.service_type = 'normal',
                        r.travel_time_min = $travel_time_min,
                        r.fare_standard_usd = $fare_standard_usd,
                        r.fare_first_usd = $fare_first_usd
                    """,
                    from_id=s["station_id"],
                    to_id=adj["station_id"],
                    line=adj["line"],
                    travel_time_min=adj["travel_time_min"],
                    fare_standard_usd=rail_fare_by_line.get(adj["line"], {}).get("standard", 1.50),
                    fare_first_usd=rail_fare_by_line.get(adj["line"], {}).get("first", 2.50),
                )

        # Create express rail links between the stations where express services stop.
        for schedule in rail_schedules:
            if schedule["service_type"] != "express":
                continue

            stops = schedule["stops_in_order"]
            times = schedule["travel_time_from_origin_min"]
            standard_fare = float(schedule["fare_classes"]["standard"]["per_stop_rate_usd"])
            first_fare = float(schedule["fare_classes"]["first"]["per_stop_rate_usd"])

            for from_id, to_id in zip(stops, stops[1:]):
                session.run(
                    """
                    MATCH (a:RailStation {station_id: $from_id})
                    MATCH (b:RailStation {station_id: $to_id})
                    MERGE (a)-[r:RAIL_EXPRESS_LINK {schedule_id: $schedule_id}]->(b)
                    SET r.line = $line,
                        r.service_type = 'express',
                        r.travel_time_min = $travel_time_min,
                        r.fare_standard_usd = $fare_standard_usd,
                        r.fare_first_usd = $fare_first_usd
                    """,
                    from_id=from_id,
                    to_id=to_id,
                    schedule_id=schedule["schedule_id"],
                    line=schedule["line"],
                    travel_time_min=times[to_id] - times[from_id],
                    fare_standard_usd=standard_fare,
                    fare_first_usd=first_fare,
                )

        # Create interchange relationships between rail and metro
        for s in rail_stations:
            metro_id = s.get("interchange_metro_station_id")
            if metro_id:
                session.run(
                    """
                    MATCH (r:RailStation {station_id: $rail_id})
                    MATCH (m:MetroStation {station_id: $metro_id})
                    MERGE (r)-[a:INTERCHANGE]->(m)
                    SET a.travel_time_min = 5,
                        a.fare_usd = 0.0
                    MERGE (m)-[b:INTERCHANGE]->(r)
                    SET b.travel_time_min = 5,
                        b.fare_usd = 0.0
                    """,
                    rail_id=s["station_id"],
                    metro_id=metro_id,
                )

    driver.close()
    print("\nNeo4j graph seeded successfully.")
    print("   Open http://localhost:7475 to explore the graph.")


if __name__ == "__main__":
    print("Connecting to Neo4j...")
    seed()
