"""
Seed PostgreSQL with all TransitFlow mock data from train-mock-data/.

Usage:
    python skeleton/seed_postgres.py

Run AFTER docker-compose up -d.
You must first design and create your tables in databases/relational/schema.sql.
Safe to re-run: implement your inserts with ON CONFLICT DO NOTHING.
"""

import json
import os
import sys

import psycopg2
from psycopg2.extras import execute_values

# ── resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR    = os.path.join(PROJECT_DIR, "train-mock-data")

sys.path.insert(0, PROJECT_DIR)
from skeleton import config as cfg


def load(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def connect():
    return psycopg2.connect(
        host=cfg.PG_HOST,
        port=cfg.PG_PORT,
        dbname=cfg.PG_DB,
        user=cfg.PG_USER,
        password=cfg.PG_PASSWORD,
    )


def insert_many(cur, table, columns, rows):
    """Bulk insert with ON CONFLICT DO NOTHING. Returns row count inserted."""
    if not rows:
        return 0
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT DO NOTHING"
    )
    execute_values(cur, sql, rows)
    return cur.rowcount


# ── seeders ──────────────────────────────────────────────────────────────────

def seed_metro_stations(cur):

    data = load("metro_stations.json")

    # -------------------------
    # metro_stations
    # -------------------------

    station_rows = [
        (
            s["station_id"],
            s["name"],
            s["is_interchange_metro"],
            s["is_interchange_national_rail"],
            s.get("interchange_national_rail_station_id")
        )
        for s in data
    ]

    n1 = insert_many(
        cur,
        "metro_stations",
        [
            "station_id",
            "name",
            "is_interchange_metro",
            "is_interchange_national_rail",
            "interchange_national_rail_station_id"
        ],
        station_rows
    )

    print(f"metro_stations: {n1} rows")


    # -------------------------
    # metro_station_lines
    # -------------------------

    line_rows = []

    for s in data:
        for line in s["lines"]:
            line_rows.append(
                (
                    s["station_id"],
                    line
                )
            )

    n2 = insert_many(
        cur,
        "metro_station_lines",
        [
            "station_id",
            "line"
        ],
        line_rows
    )

    print(f"metro_station_lines: {n2} rows")


    # -------------------------
    # metro_station_connections
    # -------------------------

    connection_rows = []

    for s in data:

        station_id = s["station_id"]

        for connection in s["adjacent_stations"]:

            connection_rows.append(
                (
                    station_id,
                    connection["station_id"],
                    connection["line"],
                    connection["travel_time_min"]
                )
            )

    n3 = insert_many(
        cur,
        "metro_station_connections",
        [
            "station_id",
            "connected_station_id",
            "line",
            "travel_time_min"
        ],
        connection_rows
    )

    print(f"metro_station_connections: {n3} rows")


def seed_national_rail_stations(cur):
    data = load("national_rail_stations.json")

    station_rows = []
    line_rows = []
    connection_rows = []

    for s in data:

        station_rows.append(
            (
                s["station_id"],
                s["name"],
                s["is_interchange_national_rail"],
                s["is_interchange_metro"],
                s["interchange_metro_station_id"]
            )
        )

        for line in s["lines"]:
            line_rows.append(
                (
                    s["station_id"],
                    line
                )
            )

        for conn in s["adjacent_stations"]:
            connection_rows.append(
                (
                    s["station_id"],
                    conn["station_id"],
                    conn["line"],
                    conn["travel_time_min"]
                )
            )

    n1 = insert_many(
        cur,
        "national_rail_stations",
        [
            "station_id",
            "name",
            "is_interchange_national_rail",
            "is_interchange_metro",
            "interchange_metro_station_id"
        ],
        station_rows
    )

    n2 = insert_many(
        cur,
        "national_rail_station_lines",
        [
            "station_id",
            "line"
        ],
        line_rows
    )

    n3 = insert_many(
        cur,
        "national_rail_station_connections",
        [
            "station_id",
            "connected_station_id",
            "line",
            "travel_time_min"
        ],
        connection_rows
    )

    print(f"national_rail_stations: {n1} rows")
    print(f"national_rail_station_lines: {n2} rows")
    print(f"national_rail_station_connections: {n3} rows")


def seed_metro_schedules(cur):

    data = load("metro_schedules.json")

    # -------------------------
    # metro_schedules
    # -------------------------

    schedule_rows = [
        (
            s["schedule_id"],
            s["line"],
            s["direction"],
            s["origin_station_id"],
            s["destination_station_id"],
            s["first_train_time"],
            s["last_train_time"],
            s["base_fare_usd"],
            s["per_stop_rate_usd"],
            s["frequency_min"]
        )
        for s in data
    ]

    n1 = insert_many(
        cur,
        "metro_schedules",
        [
            "schedule_id",
            "line",
            "direction",
            "origin_station_id",
            "destination_station_id",
            "first_train_time",
            "last_train_time",
            "base_fare_usd",
            "per_stop_rate_usd",
            "frequency_min"
        ],
        schedule_rows
    )

    print(f"metro_schedules: {n1} rows")


    # -------------------------
    # metro_schedule_stops
    # -------------------------

    stop_rows = []

    for s in data:

        schedule_id = s["schedule_id"]

        for idx, station_id in enumerate(s["stops_in_order"]):

            stop_rows.append(
                (
                    schedule_id,
                    station_id,
                    idx + 1,
                    s["travel_time_from_origin_min"][station_id]
                )
            )

    n2 = insert_many(
        cur,
        "metro_schedule_stops",
        [
            "schedule_id",
            "station_id",
            "stop_order",
            "travel_time_from_origin_min"
        ],
        stop_rows
    )

    print(f"metro_schedule_stops: {n2} rows")


def seed_national_rail_schedules(cur):
    data = load("national_rail_schedules.json")

    schedule_rows = []
    stop_rows = []
    fare_rows = []

    for s in data:

        schedule_rows.append(
            (
                s["schedule_id"],
                s["line"],
                s["service_type"],
                s["direction"],
                s["origin_station_id"],
                s["destination_station_id"],
                s["first_train_time"],
                s["last_train_time"],
                s["frequency_min"]
            )
        )

        passed = s.get("passed_through_stations", [])

        for idx, station_id in enumerate(s["stops_in_order"]):

            stop_rows.append(
                (
                    s["schedule_id"],
                    station_id,
                    idx + 1,
                    s["travel_time_from_origin_min"][station_id],
                    False
                )
            )

        for station_id in passed:

            stop_rows.append(
                (
                    s["schedule_id"],
                    station_id,
                    -1,
                    0,
                    True
                )
            )

        for fare_class, fare_data in s["fare_classes"].items():

            fare_rows.append(
                (
                    s["schedule_id"],
                    fare_class,
                    fare_data["base_fare_usd"],
                    fare_data["per_stop_rate_usd"]
                )
            )

    n1 = insert_many(
        cur,
        "national_rail_schedules",
        [
            "schedule_id",
            "line",
            "service_type",
            "direction",
            "origin_station_id",
            "destination_station_id",
            "first_train_time",
            "last_train_time",
            "frequency_min"
        ],
        schedule_rows
    )

    n2 = insert_many(
        cur,
        "national_rail_schedule_stops",
        [
            "schedule_id",
            "station_id",
            "stop_order",
            "travel_time_from_origin_min",
            "is_passed_through"
        ],
        stop_rows
    )

    n3 = insert_many(
        cur,
        "national_rail_fare_classes",
        [
            "schedule_id",
            "fare_class",
            "base_fare_usd",
            "per_stop_rate_usd"
        ],
        fare_rows
    )

    print(f"national_rail_schedules: {n1} rows")
    print(f"national_rail_schedule_stops: {n2} rows")
    print(f"national_rail_fare_classes: {n3} rows")


def seed_seat_layouts(cur):

    data = load("national_rail_seat_layouts.json")

    layout_rows = []
    seat_rows = []

    for layout in data:

        layout_rows.append(
            (
                layout["layout_id"],
                layout["schedule_id"]
            )
        )

        for coach in layout["coaches"]:

            for seat in coach["seats"]:

                seat_rows.append(
                    (
                        layout["layout_id"],
                        coach["coach"],
                        coach["fare_class"],
                        seat["seat_id"],
                        seat["row"],
                        seat["column"]
                    )
                )

    n1 = insert_many(
        cur,
        "national_rail_seat_layouts",
        [
            "layout_id",
            "schedule_id"
        ],
        layout_rows
    )

    n2 = insert_many(
        cur,
        "national_rail_seats",
        [
            "layout_id",
            "coach",
            "fare_class",
            "seat_id",
            "row_number",
            "column_letter"
        ],
        seat_rows
    )

    print(f"national_rail_seat_layouts: {n1} rows")
    print(f"national_rail_seats: {n2} rows")


def seed_users(cur):

    data = load("registered_users.json")

    rows = [
        (
            u["user_id"],
            u["full_name"],
            u["email"],
            u["password"],
            u["phone"],
            u["date_of_birth"],
            u["secret_question"],
            u["secret_answer"],
            u["registered_at"],
            u["is_active"]
        )
        for u in data
    ]

    n = insert_many(
        cur,
        "registered_users",
        [
            "user_id",
            "full_name",
            "email",
            "password",
            "phone",
            "date_of_birth",
            "secret_question",
            "secret_answer",
            "registered_at",
            "is_active"
        ],
        rows
    )

    print(f"registered_users: {n} rows")


def seed_national_rail_bookings(cur):

    data = load("bookings.json")

    rows = [
        (
            b["booking_id"],
            b["user_id"],
            b["schedule_id"],
            b["origin_station_id"],
            b["destination_station_id"],
            b["travel_date"],
            b["departure_time"],
            b["ticket_type"],
            b["fare_class"],
            b["coach"],
            b["seat_id"],
            b["stops_travelled"],
            b["amount_usd"],
            b["status"],
            b["booked_at"],
            b["travelled_at"]
        )
        for b in data
    ]

    n = insert_many(
        cur,
        "bookings",
        [
            "booking_id",
            "user_id",
            "schedule_id",
            "origin_station_id",
            "destination_station_id",
            "travel_date",
            "departure_time",
            "ticket_type",
            "fare_class",
            "coach",
            "seat_id",
            "stops_travelled",
            "amount_usd",
            "status",
            "booked_at",
            "travelled_at"
        ],
        rows
    )

    print(f"bookings: {n} rows")


def seed_metro_travels(cur):

    data = load("metro_travel_history.json")

    rows = [
        (
            t["trip_id"],
            t["user_id"],
            t["schedule_id"],
            t["origin_station_id"],
            t["destination_station_id"],
            t["travel_date"],
            t["ticket_type"],
            t.get("day_pass_ref"),
            t["stops_travelled"],
            t["amount_usd"],
            t["status"],
            t["purchased_at"],
            t["travelled_at"]
        )
        for t in data
    ]

    n = insert_many(
        cur,
        "metro_travel_history",
        [
            "trip_id",
            "user_id",
            "schedule_id",
            "origin_station_id",
            "destination_station_id",
            "travel_date",
            "ticket_type",
            "day_pass_ref",
            "stops_travelled",
            "amount_usd",
            "status",
            "purchased_at",
            "travelled_at"
        ],
        rows
    )

    print(f"metro_travel_history: {n} rows")


def seed_payments(cur):

    data = load("payments.json")

    rows = [
        (
            p["payment_id"],
            p["booking_id"],
            p["amount_usd"],
            p["method"],
            p["status"],
            p["paid_at"]
        )
        for p in data
    ]

    n = insert_many(
        cur,
        "payments",
        [
            "payment_id",
            "reference_id",
            "amount_usd",
            "method",
            "status",
            "paid_at"
        ],
        rows
    )

    print(f"payments: {n} rows")


def seed_feedback(cur):

    data = load("feedback.json")

    rows = [
        (
            f["feedback_id"],
            f["booking_id"],
            f["user_id"],
            f["rating"],
            f["comment"],
            f["submitted_at"]
        )
        for f in data
    ]

    n = insert_many(
        cur,
        "feedback",
        [
            "feedback_id",
            "reference_id",
            "user_id",
            "rating",
            "comment",
            "submitted_at"
        ],
        rows
    )

    print(f"feedback: {n} rows")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to PostgreSQL...")
    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Seeding tables (dependency order):")
        seed_metro_stations(cur)
        seed_national_rail_stations(cur)
        seed_metro_schedules(cur)
        seed_national_rail_schedules(cur)
        seed_seat_layouts(cur)
        seed_users(cur)
        seed_national_rail_bookings(cur)
        seed_metro_travels(cur)
        seed_payments(cur)
        seed_feedback(cur)
        conn.commit()
        print("\nAll done. Database seeded successfully.")
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
