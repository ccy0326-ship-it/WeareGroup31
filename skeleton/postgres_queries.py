"""TransitFlow — PostgreSQL / Relational Database Layer
=====================================================
This module handles all queries to PostgreSQL.

TWO ROLES ARE SERVED HERE:
  1. Relational  → dual-network transit (metro + national rail),
                   availability, fares, bookings, seat selection
  2. Vector      → policy document similarity search (pgvector)

STUDENT TASK
------------
Design your schema in databases/relational/schema.sql, seed it with
skeleton/seed_postgres.py, then implement the query functions below.

Functions prefixed with `query_`  are read-only lookups called by the agent.
Functions prefixed with `execute_` are write operations (booking/cancellation).

The vector functions (query_policy_vector_search, store_policy_document)
are already implemented — do not modify them.
"""

from __future__ import annotations

import json
import random
import string
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.errors import UniqueViolation

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from skeleton.config import PG_DSN, VECTOR_TOP_K, VECTOR_SIMILARITY_THRESHOLD

ph = PasswordHasher()

def _connect():
    """Return a new psycopg2 connection with autocommit enabled."""
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    return conn


def _gen_booking_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK-{suffix}"


def _gen_payment_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PM-{suffix}"


# ── Example ───────────────────────────────────────────────────────────────────
# The block below shows the query pattern: open a cursor, run SQL, return rows.
# Use _connect() for read-only queries; for write operations use a manual
# connection with conn.commit() / conn.rollback() (see execute_booking below).

def example_query() -> dict:
    """Example: returns the name of the connected database."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT current_database() AS db;")
            return dict(cur.fetchone())

# TODO: Implement the query_ and execute_ functions below.
# ─────────────────────────────────────────────────────────────────────────────


# ── NATIONAL RAIL AVAILABILITY ────────────────────────────────────────────────

def query_national_rail_availability(
    origin_id: str,
    destination_id: str,
    travel_date: Optional[str] = None,
) -> list[dict]:
    """
    Return national rail schedules that serve both origin and destination stations
    in the correct order, along with seat occupancy for the requested travel date.
    """

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""

            SELECT DISTINCT
                nrs.schedule_id,
                nrs.first_train_time AS departure_time,
                nrs.last_train_time AS arrival_time,
                COUNT(b.booking_id) AS booked_seats

            FROM national_rail_schedules nrs

            JOIN national_rail_schedule_stops origin_stop
                ON nrs.schedule_id = origin_stop.schedule_id

            JOIN national_rail_schedule_stops destination_stop
                ON nrs.schedule_id = destination_stop.schedule_id

            LEFT JOIN bookings b
                ON nrs.schedule_id = b.schedule_id
                AND b.travel_date = %s
                AND b.status = 'confirmed'

            WHERE origin_stop.station_id = %s
              AND destination_stop.station_id = %s
              AND origin_stop.stop_order < destination_stop.stop_order

            GROUP BY
                nrs.schedule_id,
                nrs.first_train_time,
                nrs.last_train_time

            ORDER BY nrs.first_train_time

            """, (
                travel_date,
                origin_id,
                destination_id
            ))

            return [dict(row) for row in cur.fetchall()]


def query_national_rail_fare(
    schedule_id: str,
    fare_class: str,
    stops_travelled: int,
) -> Optional[dict]:
    """
    Calculate the fare for a national rail journey.

    Args:
        schedule_id:     e.g. "NR_SCH01"
        fare_class:      "standard" or "first"
        stops_travelled: number of stops between origin and destination (inclusive)

    Returns:
        dict with fare_class, base_fare_usd, per_stop_rate_usd, total_fare_usd
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
            SELECT
            fare_class,
            base_fare_usd,
            per_stop_rate_usd
            FROM national_rail_fare_classes
            WHERE schedule_id = %s
            AND fare_class = %s
            """, (schedule_id, fare_class))

            row = cur.fetchone()

        if not row:
            return None

        total = (
            row["base_fare_usd"] +
            row["per_stop_rate_usd"] * stops_travelled
        )

        return {
        "fare_class": row["fare_class"],
        "base_fare_usd": row["base_fare_usd"],
        "per_stop_rate_usd": row["per_stop_rate_usd"],
        "total_fare_usd": round(total, 2)
        }

# ── METRO SCHEDULES & FARE ────────────────────────────────────────────────────

def query_metro_schedules(origin_id: str, destination_id: str) -> list[dict]:
    """
    Return metro schedules that serve both origin and destination
    in the correct order.
    """

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""

            SELECT DISTINCT
                ms.schedule_id,
                ms.line,
                ms.first_train_time AS departure_time,
                ms.last_train_time AS arrival_time,
                ms.base_fare_usd,
                ms.per_stop_rate_usd

            FROM metro_schedules ms

            JOIN metro_schedule_stops origin_stop
                ON ms.schedule_id = origin_stop.schedule_id

            JOIN metro_schedule_stops destination_stop
                ON ms.schedule_id = destination_stop.schedule_id

            WHERE origin_stop.station_id = %s
              AND destination_stop.station_id = %s
              AND origin_stop.stop_order < destination_stop.stop_order

            ORDER BY ms.first_train_time

            """, (
                origin_id,
                destination_id
            ))

            return [dict(row) for row in cur.fetchall()]


def query_metro_fare(schedule_id: str, stops_travelled: int) -> Optional[dict]:
    """
    Calculate the metro fare for a single-ticket journey.

    Args:
        schedule_id:     e.g. "MS_SCH01"
        stops_travelled: number of stops between origin and destination

    Returns:
        dict with base_fare_usd, per_stop_rate_usd, total_fare_usd
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
            SELECT
                base_fare_usd,
                per_stop_rate_usd
            FROM metro_schedules
            WHERE schedule_id = %s
            """, (schedule_id,))

            row = cur.fetchone()

        if not row:
            return None

        total = (
            row["base_fare_usd"] +
            row["per_stop_rate_usd"] * stops_travelled
        )

        return {
            "base_fare_usd": row["base_fare_usd"],
            "per_stop_rate_usd": row["per_stop_rate_usd"],
            "total_fare_usd": round(total, 2)
        }

# ── SEAT SELECTION ────────────────────────────────────────────────────────────

def query_available_seats(
    schedule_id: str,
    travel_date: str,
    fare_class: str,
) -> list[dict]:
    """
    Return available seats for a national rail journey on a given date.

    Args:
        schedule_id:  e.g. "NR_SCH01"
        travel_date:  e.g. "2025-06-01"
        fare_class:   "standard" or "first"

    Returns:
        List of dicts: {seat_id, coach, row, column}
    """

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""

            SELECT
                s.seat_id,
                s.coach,
                s.row_number AS row,
                s.column_letter AS column

            FROM national_rail_seats s

            JOIN national_rail_seat_layouts l
                ON s.layout_id = l.layout_id

            WHERE l.schedule_id = %s
              AND s.fare_class = %s

              AND s.seat_id NOT IN (

                    SELECT b.seat_id
                    FROM bookings b
                    WHERE b.schedule_id = %s
                      AND b.travel_date = %s
                      AND b.status = 'confirmed'

              )

            ORDER BY s.coach, s.row_number, s.column_letter

            """, (
                schedule_id,
                fare_class,
                schedule_id,
                travel_date
            ))

            return [dict(row) for row in cur.fetchall()]

def auto_select_adjacent_seats(available_seats: list[dict], count: int) -> list[str]:
    """
    Select `count` seats that are as close together as possible (same row preferred,
    then adjacent rows). Returns a list of seat_ids.

    Args:
        available_seats: output of query_available_seats()
        count:           number of seats needed
    """
    if not available_seats or count <= 0:
        return []
    if count >= len(available_seats):
        return [s["seat_id"] for s in available_seats[:count]]

    from collections import defaultdict
    rows: dict[int, list[dict]] = defaultdict(list)
    for seat in available_seats:
        rows[seat["row"]].append(seat)

    for row_seats in sorted(rows.values(), key=lambda s: s[0]["row"]):
        if len(row_seats) >= count:
            return [s["seat_id"] for s in row_seats[:count]]

    sorted_seats = sorted(available_seats, key=lambda s: (s["row"], s["column"]))
    return [s["seat_id"] for s in sorted_seats[:count]]


# ── USER & BOOKING QUERIES ────────────────────────────────────────────────────

def query_user_profile(user_email: str) -> Optional[dict]:
    """Return a user's profile by email."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
            SELECT *
            FROM registered_users
            WHERE email = %s
            """, (user_email,))

            row = cur.fetchone()

        return dict(row) if row else None


def query_user_bookings(user_email: str) -> dict:
    """
    Return a user's combined booking history (national rail + metro).

    Returns:
        dict with keys 'national_rail' (list) and 'metro' (list)
    """

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # National rail bookings
            cur.execute("""
            SELECT b.*
            FROM bookings b
            JOIN registered_users u
                ON b.user_id = u.user_id
            WHERE u.email = %s
            ORDER BY b.travel_date DESC
            """, (user_email,))

            bookings = [dict(row) for row in cur.fetchall()]

            # Metro travel history
            cur.execute("""
            SELECT m.*
            FROM metro_travel_history m
            JOIN registered_users u
                ON m.user_id = u.user_id
            WHERE u.email = %s
            ORDER BY m.travel_date DESC
            """, (user_email,))

            metro_bookings = [dict(row) for row in cur.fetchall()]

        return {
            "national_rail": bookings,
            "metro": metro_bookings
        }


def calculate_stops_travelled(
    schedule_id: str,
    origin_station_id: str,
    destination_station_id: str
) -> Optional[int]:

    with _connect() as conn:
        with conn.cursor() as cur:

            cur.execute("""

            SELECT
                destination.stop_order - origin.stop_order AS stops

            FROM national_rail_schedule_stops origin

            JOIN national_rail_schedule_stops destination
                ON origin.schedule_id = destination.schedule_id

            WHERE origin.schedule_id = %s
              AND origin.station_id = %s
              AND destination.station_id = %s

            """, (
                schedule_id,
                origin_station_id,
                destination_station_id
            ))

            row = cur.fetchone()

        if not row:
            return None

        return row[0]

def query_payment_info(reference_id: str) -> Optional[dict]:
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
            SELECT *
            FROM payments
            WHERE reference_id = %s
            """, (reference_id,))

            row = cur.fetchone()

        return dict(row) if row else None

# ── TRANSACTIONAL OPERATIONS ──────────────────────────────────────────────────

def execute_booking(
    user_id: str,
    schedule_id: str,
    origin_station_id: str,
    destination_station_id: str,
    travel_date: str,
    fare_class: str,
    seat_id: str,
    ticket_type: str = "single",
) -> tuple[bool, dict | str]:
    """
    Create a national rail booking for a logged-in user.

    Args:
        user_id:                e.g. "RU01" — must match the logged-in user
        schedule_id:            e.g. "NR_SCH01"
        origin_station_id:      e.g. "NR01"
        destination_station_id: e.g. "NR05"
        travel_date:            e.g. "2025-06-01"
        fare_class:             "standard" or "first"
        seat_id:                e.g. "B05" (or "any" to auto-assign)
        ticket_type:            "single" (default) or "return"

    Returns:
        (True, booking_dict)   on success
        (False, error_message) on failure
    """

    conn = psycopg2.connect(PG_DSN)

    try:
        # Transaction ensures booking and payment are committed together.
        # This prevents partial data if one operation fails.
        conn.autocommit = False

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            #Check if seat already booked
            cur.execute("""
            SELECT 1
            FROM bookings
            WHERE schedule_id = %s
              AND travel_date = %s
              AND seat_id = %s
              AND status = 'confirmed'
            """, (
                schedule_id,
                travel_date,
                seat_id
            ))

            existing = cur.fetchone()
            
            #Prevent double-booking of the same seat on the same journey date
            if existing:
                conn.rollback()
                return (False, "Seat already booked")

            # Generate IDs
            booking_id = _gen_booking_id()
            payment_id = _gen_payment_id()

            # Calculate fare
            stops_travelled = calculate_stops_travelled(
                schedule_id,
                origin_station_id,
                destination_station_id
            ) 

            if stops_travelled is None:
                conn.rollback()
                return (False, "Invalid station route")
            
            fare_info = query_national_rail_fare(
                schedule_id,
                fare_class,
                stops_travelled
            )

            if not fare_info:
                conn.rollback()
                return (False, "Fare not found")

            amount_usd = fare_info["total_fare_usd"]
            
            #Insert booking
            cur.execute("""
            INSERT INTO bookings (
                booking_id,
                user_id,
                schedule_id,
                origin_station_id,
                destination_station_id,
                travel_date,
                departure_time,
                ticket_type,
                fare_class,
                seat_id,
                stops_travelled,
                amount_usd,
                status,
                booked_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, NOW()
            )
            """, (
                booking_id,
                user_id,
                schedule_id,
                origin_station_id,
                destination_station_id,
                travel_date,
                "09:00",
                ticket_type,
                fare_class,
                seat_id,
                stops_travelled,
                amount_usd,
                "confirmed"
            ))

            # Insert payment
            cur.execute("""
            INSERT INTO payments (
                payment_id,
                reference_id,
                amount_usd,
                method,
                status,
                paid_at
            )
            VALUES (
                %s, %s, %s, %s, %s, NOW()
            )
            """, (
                payment_id,
                booking_id,
                amount_usd,
                "credit_card",
                "paid"
            ))

            conn.commit()

            return (
                True,
                {
                    "booking_id": booking_id,
                    "payment_id": payment_id,
                    "seat_id": seat_id,
                    "status": "confirmed"
                }
            )

    except Exception as e:

        conn.rollback()
        return (False, str(e))

    finally:
        conn.close()

def execute_cancellation(booking_id: str, user_id: str) -> tuple[bool, dict | str]:
    """
    Cancel a national rail booking owned by the given user.

    Returns:
        (True, result_dict)
        (False, error_message)
    """

    conn = psycopg2.connect(PG_DSN)

    try:

        # Transaction ensures cancellation update is safely committed
        conn.autocommit = False

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Verify booking belongs to the requesting user
            cur.execute("""
            SELECT *
            FROM bookings
            WHERE booking_id = %s
              AND user_id = %s
            """, (booking_id, user_id))

            booking = cur.fetchone()

            if not booking:
                conn.rollback()
                return (False, "Booking not found")

            # Prevent cancelling an already cancelled booking
            if booking["status"] == "cancelled":
                conn.rollback()
                return (False, "Booking already cancelled")

            refund_amount = float(booking["amount_usd"]) * 0.8

            # Update booking status to cancelled
            cur.execute("""
            UPDATE bookings
            SET status = 'cancelled'
            WHERE booking_id = %s
            """, (booking_id,))

            conn.commit()

            return (
                True,
                {
                    "booking_id": booking_id,
                    "refund_amount_usd": round(refund_amount, 2),
                    "status": "cancelled"
                }
            )

    except Exception as e:

        conn.rollback()
        return (False, str(e))

    finally:
        conn.close()

# ── AUTHENTICATION QUERIES ────────────────────────────────────────────────────

def register_user(
    email: str,
    first_name: str,
    surname: str,
    year_of_birth: int,
    password: str,
    secret_question: str,
    secret_answer: str,
) -> tuple[bool, str]:
    """
    Register a new user.
    Returns (True, user_id) on success or (False, error_message) on failure.

    Passwords are securely hashed using Argon2 before storage.
    """

    hashed_password = ph.hash(password)

    user_id = "RU" + ''.join(random.choices(string.digits, k=4))

    full_name = f"{first_name} {surname}"

    try:
        with _connect() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                INSERT INTO registered_users (
                    user_id,
                    full_name,
                    email,
                    password,
                    date_of_birth,
                    secret_question,
                    secret_answer,
                    registered_at,
                    is_active
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    NOW(), TRUE
                )
                """, (
                    user_id,
                    full_name,
                    email,
                    hashed_password,
                    f"{year_of_birth}-01-01",
                    secret_question,
                    secret_answer
                ))

        return (True, user_id)

    except UniqueViolation:
        return (False, "Email already registered")

    except Exception as e:
        return (False, str(e))


def login_user(email: str, password: str) -> Optional[dict]:
    """
    Verify credentials. Returns a user dict on success or None on failure.
    Dict keys: user_id, email, full_name, phone, date_of_birth, is_active.
    """

    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
            SELECT
                user_id,
                email,
                full_name,
                phone,
                date_of_birth,
                is_active,
                password
            FROM registered_users
            WHERE email = %s
              AND is_active = TRUE
            """, (email,))

            row = cur.fetchone()

        if not row:
            return None

        try:
            ph.verify(row["password"], password)

            return {
                "user_id": row["user_id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "phone": row["phone"],
                "date_of_birth": row["date_of_birth"],
                "is_active": row["is_active"]
            }

        except VerifyMismatchError:
            return None


def get_user_secret_question(email: str) -> Optional[str]:
    """Return the secret question for a registered email, or None if not found."""

    with _connect() as conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT secret_question
            FROM registered_users
            WHERE email = %s
            """, (email,))

            row = cur.fetchone()

        return row[0] if row else None


def verify_secret_answer(email: str, answer: str) -> bool:
    """
    Return True if the provided answer matches the stored
    secret answer (case-insensitive).
    """

    with _connect() as conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT secret_answer
            FROM registered_users
            WHERE email = %s
            """, (email,))

            row = cur.fetchone()

        if not row:
            return False

        stored_answer = row[0]

        return stored_answer.lower() == answer.lower()


def update_password(email: str, new_password: str) -> bool:
    """
    Update the password for a user using secure Argon2 hashing.
    Returns True if the password was updated successfully.
    """

    hashed_password = ph.hash(new_password)

    with _connect() as conn:
        with conn.cursor() as cur:

            cur.execute("""
            UPDATE registered_users
            SET password = %s
            WHERE email = %s
            """, (
                hashed_password,
                email
            ))

            return cur.rowcount > 0


# ── VECTOR / RAG QUERIES — do not modify ─────────────────────────────────────

def query_policy_vector_search(embedding: list[float], top_k: int = VECTOR_TOP_K) -> list[dict]:
    """
    Find the most relevant policy documents for a given query embedding.

    Args:
        embedding: Query vector from llm.embed(user_question)
        top_k:     Number of results to return

    Returns:
        List of dicts with title, category, content, and similarity score
    """
    sql = """
        SELECT
            title,
            category,
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM policy_documents
        WHERE 1 - (embedding <=> %s::vector) > %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (vec_str, vec_str, VECTOR_SIMILARITY_THRESHOLD, vec_str, top_k))
            return [dict(row) for row in cur.fetchall()]


def store_policy_document(
    title: str,
    category: str,
    content: str,
    embedding: list[float],
    source_file: str = "",
) -> int:
    """
    Insert a policy document with its embedding into the database.
    Used by skeleton/seed_vectors.py — students don't need to call this directly.

    Returns:
        The new document's id
    """
    sql = """
        INSERT INTO policy_documents (title, category, content, embedding, source_file)
        VALUES (%s, %s, %s, %s::vector, %s)
        RETURNING id
    """
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (title, category, content, vec_str, source_file))
            return cur.fetchone()[0]
