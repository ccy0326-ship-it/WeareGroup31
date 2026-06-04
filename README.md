# TransitFlow — Intelligent Rail Assistant

TransitFlow is a multi-database intelligent transportation assistant developed for IM2002 Database Management.

The system combines three different database technologies to support natural language transit queries:

* PostgreSQL (Relational Database)
* Neo4j (Graph Database)
* pgvector (Vector Database)

Users can interact with the system through an AI-powered assistant that automatically selects the appropriate database tools to answer transportation, booking, routing, and policy-related questions.

---

# System Overview

TransitFlow models a fictional public transportation system consisting of:

## City Metro Network

* 4 metro lines
* 20 stations
* Same-day ticket purchases
* No seat reservations

## National Rail Network

* 2 rail lines
* 10 stations
* Advance ticket booking
* Seat reservation support
* Multiple fare classes

The assistant supports both networks and can provide cross-network routing recommendations.

---

# Multi-Database Architecture

## PostgreSQL — Relational Database

The relational database stores structured operational data including:

* Registered users
* Authentication records
* Metro stations and schedules
* National rail stations and schedules
* Fare structures
* Seat layouts and seat inventory
* Bookings
* Payments
* Travel history
* Feedback

Implemented Features:

* Availability search
* Fare calculation
* Seat selection
* Booking creation
* Booking cancellation
* Refund calculation
* User profile retrieval
* Booking history retrieval

Password security is implemented using Argon2 password hashing.

---

## Neo4j — Graph Database

Neo4j models the transportation network as connected stations and routes.

Implemented Features:

* Fastest route search
* Cheapest route search
* Alternative route generation
* Interchange path discovery
* Delay ripple analysis
* Cross-network route planning

The graph database enables path-based queries that would be significantly more complex using traditional relational joins.

---

## pgvector — Vector Database

Policy documents are embedded into vectors and stored in PostgreSQL using pgvector.

Supported policy categories include:

* Ticket policies
* Booking rules
* Refund policies
* Passenger conduct policies
* Travel regulations

Implemented Features:

* Semantic similarity search
* Policy retrieval
* Retrieval-Augmented Generation (RAG)

This allows users to ask natural language questions about policies without relying on exact keyword matches.

---

# Intelligent Agent

The TransitFlow assistant uses tool-calling to determine which database should answer a user query.

Examples:

| User Question                           | Database Used |
| --------------------------------------- | ------------- |
| Available trains from NR01 to NR05?     | PostgreSQL    |
| Cheapest route between stations?        | Neo4j         |
| What is the refund policy?              | pgvector      |
| Which stations are affected by a delay? | Neo4j         |
| Show my bookings.                       | PostgreSQL    |

The agent combines database results with LLM reasoning to generate final responses.

---

# Project Structure

```text
TransitFlow

├── databases
│   ├── relational
│   │   ├── schema.sql
│   │   └── queries.py
│   │
│   ├── graph
│   │   └── queries.py
│   │
│   └── vector
│
├── skeleton
│   ├── agent.py
│   ├── seed_postgres.py
│   ├── seed_neo4j.py
│   ├── seed_vectors.py
│   └── ui.py
│
├── train-mock-data
│
├── docker-compose.yml
└── README.md
```

---

# Task 6 Extension

The project includes an optional extension that enhances both graph intelligence and vector database reliability.

Features include:

* Fastest route discovery
* Cheapest route discovery
* Alternative routes avoiding disrupted stations
* Enhanced interchange routing
* Configurable delay ripple analysis
* Repeatable RAG vector seeding
* Deterministic policy retrieval formatting

Documentation for the extension can be found in:

```text
TASK6.md
```

---

# Technologies Used

* Python
* PostgreSQL 16
* pgvector
* Neo4j 5
* Docker
* Gradio
* Argon2
* Ollama / LLM Tool Calling

---

# AI Collaboration Guidelines

Generative AI tools (including ChatGPT) were used during development for:

* Database design review
* SQL debugging
* Cypher query development
* Python debugging
* Documentation support
* Normalization review
* RAG implementation guidance

All AI-generated suggestions were reviewed, tested, and validated by team members before being incorporated into the project.

Final responsibility for all submitted code and documentation remains with the project team.
