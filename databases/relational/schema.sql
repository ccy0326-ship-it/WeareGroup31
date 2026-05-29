-- ============================================================
--  TransitFlow PostgreSQL Schema
--  Seed data is loaded separately by: python skeleton/seed_postgres.py
--
--  TWO ROLES:
--    1. Relational  → dual-network transit data you design below
--    2. Vector      → policy documents for RAG (provided — do not modify)
-- ============================================================

-- ============================================================
--  STUDENT TASK — Design and create your relational tables here

-- VARCHAR IDs are used because the provided mock JSON data
-- already contains custom-readable IDs such as RU01 and BK001.
-- Human-readable IDs simplify debugging and match the provided coursework dataset.
-- Therefore VARCHAR identifiers are preferred over UUID or SERIAL keys.
CREATE TABLE IF NOT EXISTS registered_users (
    user_id VARCHAR(10) PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(100) UNIQUE NOT NULL,

    -- Password stored using Argon2 hash (never plain text)
    password VARCHAR(255) NOT NULL,

    phone VARCHAR(20),

    date_of_birth DATE,

    secret_question TEXT,

    -- Secret answers should also be securely hashed in production
    secret_answer TEXT,

    registered_at TIMESTAMPTZ DEFAULT NOW(),

    is_active BOOLEAN DEFAULT TRUE
);


CREATE TABLE IF NOT EXISTS metro_stations (

    station_id VARCHAR(10) PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    is_interchange_metro BOOLEAN DEFAULT FALSE,

    is_interchange_national_rail BOOLEAN DEFAULT FALSE,

    interchange_national_rail_station_id VARCHAR(10)

);


CREATE TABLE IF NOT EXISTS metro_station_lines (

    station_id VARCHAR(10) NOT NULL,

    line VARCHAR(10) NOT NULL,

    PRIMARY KEY (station_id, line),

    FOREIGN KEY (station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE CASCADE

);

CREATE TABLE IF NOT EXISTS metro_station_connections (

    station_id VARCHAR(10) NOT NULL,

    connected_station_id VARCHAR(10) NOT NULL,

    line VARCHAR(10) NOT NULL,

    travel_time_min INT NOT NULL,

    PRIMARY KEY (station_id, connected_station_id, line),

    FOREIGN KEY (station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE CASCADE,

    FOREIGN KEY (connected_station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metro_travel_history (

    trip_id VARCHAR(20) PRIMARY KEY,

    user_id VARCHAR(10) NOT NULL,

    schedule_id VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(10) NOT NULL,

    destination_station_id VARCHAR(10) NOT NULL,

    travel_date DATE NOT NULL,

    ticket_type VARCHAR(20)
    CHECK (ticket_type IN ('single', 'day_pass')),

    day_pass_ref VARCHAR(20),

    stops_travelled INT,

    amount_usd DECIMAL(6,2),

    status VARCHAR(20)
    CHECK (status IN ('completed', 'cancelled')),

    purchased_at TIMESTAMPTZ,

    travelled_at TIMESTAMPTZ,

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)
        ON DELETE CASCADE

);


CREATE TABLE IF NOT EXISTS national_rail_stations (

    station_id VARCHAR(10) PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    is_interchange_national_rail BOOLEAN DEFAULT FALSE,

    is_interchange_metro BOOLEAN DEFAULT FALSE,

    interchange_metro_station_id VARCHAR(10)

);


CREATE TABLE IF NOT EXISTS national_rail_station_lines (

    station_id VARCHAR(10) NOT NULL,

    line VARCHAR(10) NOT NULL,

    PRIMARY KEY (station_id, line),

    FOREIGN KEY (station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS national_rail_station_connections (

    station_id VARCHAR(10) NOT NULL,

    connected_station_id VARCHAR(10) NOT NULL,

    line VARCHAR(10) NOT NULL,

    travel_time_min INT NOT NULL,

    PRIMARY KEY (station_id, connected_station_id, line),

    FOREIGN KEY (station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE CASCADE,

    FOREIGN KEY (connected_station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS national_rail_schedules (

    schedule_id VARCHAR(20) PRIMARY KEY,

    line VARCHAR(10) NOT NULL,

    service_type VARCHAR(20) NOT NULL,

    direction VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(10) NOT NULL,

    destination_station_id VARCHAR(10) NOT NULL,

    first_train_time TIME NOT NULL,

    last_train_time TIME NOT NULL,

    frequency_min INT NOT NULL,

    FOREIGN KEY (origin_station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (destination_station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE RESTRICT
);


-- Stops are normalized into a separate table
-- to support flexible route traversal and fare calculation.
CREATE TABLE IF NOT EXISTS national_rail_schedule_stops (

    schedule_id VARCHAR(20) NOT NULL,

    station_id VARCHAR(10) NOT NULL,

    stop_order INT NOT NULL,

    travel_time_from_origin_min INT NOT NULL,

    is_passed_through BOOLEAN DEFAULT FALSE,

    PRIMARY KEY (schedule_id, station_id),

    FOREIGN KEY (schedule_id)
        REFERENCES national_rail_schedules(schedule_id)
        ON DELETE CASCADE,

    FOREIGN KEY (station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS national_rail_fare_classes (

    schedule_id VARCHAR(20) NOT NULL,

    fare_class VARCHAR(20) NOT NULL,

    base_fare_usd DECIMAL(6,2) NOT NULL,

    per_stop_rate_usd DECIMAL(6,2) NOT NULL,

    PRIMARY KEY (schedule_id, fare_class),

    FOREIGN KEY (schedule_id)
        REFERENCES national_rail_schedules(schedule_id)
        ON DELETE CASCADE
);


-- Booking records are normally cancelled instead of deleted
-- to preserve journey and payment history.
CREATE TABLE IF NOT EXISTS bookings (
    booking_id VARCHAR(20) PRIMARY KEY,

    user_id VARCHAR(10) NOT NULL,

    schedule_id VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(20) NOT NULL,

    destination_station_id VARCHAR(20) NOT NULL,

    travel_date DATE NOT NULL,

    departure_time TIME NOT NULL,

    ticket_type VARCHAR(20)
    CHECK (ticket_type IN ('single', 'return')),

    fare_class VARCHAR(20)
    CHECK (fare_class IN ('standard', 'first')),

    coach VARCHAR(10),

    seat_id VARCHAR(10),

    stops_travelled INT,

    amount_usd DECIMAL(6,2),

    status VARCHAR(20)
    CHECK (status IN ('confirmed', 'cancelled', 'completed')),

    booked_at TIMESTAMPTZ DEFAULT NOW(),

    travelled_at TIMESTAMPTZ,

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)
        ON DELETE CASCADE,

    FOREIGN KEY (schedule_id)
        REFERENCES national_rail_schedules(schedule_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (origin_station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (destination_station_id)
        REFERENCES national_rail_stations(station_id)
        ON DELETE RESTRICT
);

-- Partial unique index prevents double-booking
-- while still allowing cancelled bookings to exist.
CREATE UNIQUE INDEX IF NOT EXISTS unique_confirmed_seat_booking
ON bookings(schedule_id, travel_date, seat_id)
WHERE status = 'confirmed';


CREATE TABLE IF NOT EXISTS national_rail_seat_layouts (

    layout_id VARCHAR(20) PRIMARY KEY,

    schedule_id VARCHAR(20) NOT NULL,

    FOREIGN KEY (schedule_id)
        REFERENCES national_rail_schedules(schedule_id)
        ON DELETE CASCADE
);


-- Seat layouts are separated from schedules
-- to support reusable carriage configurations.
CREATE TABLE IF NOT EXISTS national_rail_seats (

    layout_id VARCHAR(20) NOT NULL,

    coach VARCHAR(10) NOT NULL,

    fare_class VARCHAR(20) NOT NULL,

    seat_id VARCHAR(10) NOT NULL,

    row_number INT NOT NULL,

    column_letter VARCHAR(5) NOT NULL,

    PRIMARY KEY (layout_id, seat_id),

    FOREIGN KEY (layout_id)
        REFERENCES national_rail_seat_layouts(layout_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metro_schedules (

    schedule_id VARCHAR(20) PRIMARY KEY,

    line VARCHAR(10) NOT NULL,

    direction VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(10) NOT NULL,

    destination_station_id VARCHAR(10) NOT NULL,

    first_train_time TIME,

    last_train_time TIME,

    base_fare_usd DECIMAL(6,2),

    per_stop_rate_usd DECIMAL(6,2),

    frequency_min INT,

    FOREIGN KEY (origin_station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (destination_station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS metro_schedule_stops (

    schedule_id VARCHAR(20) NOT NULL,

    station_id VARCHAR(10) NOT NULL,

    stop_order INT NOT NULL,

    travel_time_from_origin_min INT NOT NULL,

    PRIMARY KEY (schedule_id, station_id),

    FOREIGN KEY (schedule_id)
        REFERENCES metro_schedules(schedule_id)
        ON DELETE CASCADE,

    FOREIGN KEY (station_id)
        REFERENCES metro_stations(station_id)
        ON DELETE CASCADE
);

-- reference_id may refer to either:
--   BKxxx → national rail bookings
--   MTxxx → metro travel history
--
-- This polymorphic design avoids invalid cross-table FK constraints.
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(20) PRIMARY KEY,

    reference_id VARCHAR(20) NOT NULL,

    amount_usd DECIMAL(8,2) NOT NULL,

    method VARCHAR(30) NOT NULL
    CHECK (
        method IN (
            'credit_card',
            'debit_card',
            'ewallet'
        )
    ),
    status VARCHAR(20) NOT NULL
    CHECK (status IN ('paid', 'pending', 'refunded')),

    paid_at TIMESTAMPTZ DEFAULT NOW()

);

-- reference_id may refer to either:
--   BKxxx → national rail bookings
--   MTxxx → metro travel history
--
-- Therefore no strict booking foreign key is enforced.
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id VARCHAR(20) PRIMARY KEY,

    reference_id VARCHAR(20) NOT NULL,

    user_id VARCHAR(10) NOT NULL,

    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),

    comment TEXT,

    submitted_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)
        ON DELETE RESTRICT
);  
--  Start from the mock data in train-mock-data/:
--    metro_stations.json, national_rail_stations.json
--    metro_schedules.json, national_rail_schedules.json
--    national_rail_seat_layouts.json
--    registered_users.json
--    bookings.json, metro_travel_history.json
--    payments.json, feedback.json
--
--  Think about:
--    - What tables do you need?
--    - What columns and data types?
--    - Which fields are primary keys? Which are foreign keys?
--    - What constraints make sense?
--
--  Apply your schema with:
--    docker-compose down -v && docker-compose up -d
-- ============================================================




-- ============================================================
--  VECTOR SCHEMA  (RAG / Help Desk) — do not modify
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_documents (
    id          SERIAL       PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    category    VARCHAR(50)  NOT NULL,  -- 'refund', 'booking', 'conduct'
    content     TEXT         NOT NULL,
    -- 768-dim  → Ollama nomic-embed-text (default)
    -- 3072-dim → Gemini gemini-embedding-001
    -- If you switch LLM_PROVIDER to gemini, change to vector(3072) and reset the database.
    embedding   vector(768),
    source_file VARCHAR(200),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_policy_documents_embedding ON policy_documents USING hnsw (embedding vector_cosine_ops);