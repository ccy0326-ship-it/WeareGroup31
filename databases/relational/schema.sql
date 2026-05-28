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
CREATE TABLE IF NOT EXISTS registered_users (
    user_id VARCHAR(10) PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(100) UNIQUE NOT NULL,

    password VARCHAR(100) NOT NULL,

    phone VARCHAR(20),

    date_of_birth DATE,

    secret_question TEXT,

    secret_answer TEXT,

    registered_at TIMESTAMPTZ,

    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id VARCHAR(20) PRIMARY KEY,

    user_id VARCHAR(10) NOT NULL,

    schedule_id VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(20) NOT NULL,

    destination_station_id VARCHAR(20) NOT NULL,

    travel_date DATE NOT NULL,

    departure_time TIME NOT NULL,

    ticket_type VARCHAR(20),

    fare_class VARCHAR(20),

    coach VARCHAR(10),

    seat_id VARCHAR(10),

    stops_travelled INT,

    amount_usd DECIMAL(6,2),

    status VARCHAR(20),

    booked_at TIMESTAMPTZ,

    travelled_at TIMESTAMPTZ,

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)
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

);

CREATE TABLE IF NOT EXISTS metro_station_connections (

    station_id VARCHAR(10) NOT NULL,

    connected_station_id VARCHAR(10) NOT NULL,

    line VARCHAR(10) NOT NULL,

    travel_time_min INT NOT NULL,

    PRIMARY KEY (station_id, connected_station_id, line),

    FOREIGN KEY (station_id)
        REFERENCES metro_stations(station_id),

    FOREIGN KEY (connected_station_id)
        REFERENCES metro_stations(station_id)

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

    frequency_min INT

);

CREATE TABLE IF NOT EXISTS metro_schedule_stops (

    schedule_id VARCHAR(20) NOT NULL,

    station_id VARCHAR(10) NOT NULL,

    stop_order INT NOT NULL,

    travel_time_from_origin_min INT NOT NULL,

    PRIMARY KEY (schedule_id, station_id)

);
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(20) PRIMARY KEY,

    booking_id VARCHAR(20) NOT NULL,

    amount_usd DECIMAL(8,2) NOT NULL,

    method VARCHAR(30) NOT NULL,

    status VARCHAR(20) NOT NULL,

    paid_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS metro_travel_history (

    trip_id VARCHAR(20) PRIMARY KEY,

    user_id VARCHAR(10) NOT NULL,

    schedule_id VARCHAR(20) NOT NULL,

    origin_station_id VARCHAR(10) NOT NULL,

    destination_station_id VARCHAR(10) NOT NULL,

    travel_date DATE NOT NULL,

    ticket_type VARCHAR(20),

    day_pass_ref VARCHAR(20),

    stops_travelled INT,

    amount_usd DECIMAL(6,2),

    status VARCHAR(20),

    purchased_at TIMESTAMPTZ,

    travelled_at TIMESTAMPTZ,

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)

);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id VARCHAR(20) PRIMARY KEY,

    booking_id VARCHAR(20) NOT NULL,

    user_id VARCHAR(10) NOT NULL,

    rating INT NOT NULL,

    comment TEXT,

    submitted_at TIMESTAMPTZ,

    FOREIGN KEY (user_id)
        REFERENCES registered_users(user_id)
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
