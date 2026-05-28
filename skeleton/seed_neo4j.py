"""
TransitFlow — Neo4j Seeder
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
    rail_stations  = _load("national_rail_stations.json")

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
                        r.travel_time_min = $travel_time_min
                    """,
                    from_id=s["station_id"],
                    to_id=adj["station_id"],
                    line=adj["line"],
                    travel_time_min=adj["travel_time_min"],
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
                        r.travel_time_min = $travel_time_min
                    """,
                    from_id=s["station_id"],
                    to_id=adj["station_id"],
                    line=adj["line"],
                    travel_time_min=adj["travel_time_min"],
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
                    SET a.travel_time_min = 5
                    MERGE (m)-[b:INTERCHANGE]->(r)
                    SET b.travel_time_min = 5
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