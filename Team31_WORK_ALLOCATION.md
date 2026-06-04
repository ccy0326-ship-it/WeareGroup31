# Work Allocation Report — Team31

## 1. Team Members

| Full Name | Student ID | GitHub Username | Email                                                         |
| --------- | ---------- | --------------- | ------------------------------------------------------------- |
| 戴睿真       | 113403525  | jui-chen1024    | [zhen7770@gmail.com](mailto:zhen7770@gmail.com)               |
| 蕭彤恩       | 113403526  | en1101          | [aa20051101@gmail.com](mailto:aa20051101@gmail.com)           |
| 欉家誼       | 113403530  | ccy0326         | [chungchiayi0326@gmail.com](mailto:chungchiayi0326@gmail.com) |
---

## 2. Task Ownership

### Code Repository

| Task                                                                                                                                             | Primary Owner | Supporting Member(s) | Notes                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- | -------------------- | --------------------------------------------------------------------------------- |
| Task 1 — Relational schema design (schema.sql)                                                                                                   | 欉家誼           | 戴睿真                  | Checked vector compatibility (embedding dimension, policy schema integration)     |
| Task 2a — Core availability & fare queries (query_national_rail_availability, query_metro_schedules, query_national_rail_fare, query_metro_fare) | 欉家誼           | 戴睿真                  | Assisted SQL query optimization for AI agent integration                          |
| Task 2b — Seat & user queries (query_available_seats, query_user_profile, query_user_bookings, query_payment_info)                               | 欉家誼           | 戴睿真                  | Assisted query structure review                                                   |
| Task 2c — Write operations (execute_booking, execute_cancellation)                                                                               | 欉家誼           | 戴睿真                  | Query integration support                                                         |
| Task 2d — Authentication queries (login_user, register_user, get_user_secret_question, verify_secret_answer, update_password)                    | 欉家誼           | 戴睿真                  | Assisted relational query integration                                             |
| Task 3 — PostgreSQL seeding (seed_postgres.py)                                                                                                   | 欉家誼           | 戴睿真                  | Managed train-mock-data JSON and vector-related data                              |
| Task 4 — Neo4j graph design & seeding (seed_neo4j.py, seed.cypher)                                                                               | 蕭彤恩           |                      | Sole developer for graph database design and seeding                              |
| Task 5 — Neo4j query functions (graph/queries.py)                                                                                                | 蕭彤恩           | 戴睿真                  | Assisted AI agent query coordination                                              |
| Task 6 — Optional extension (Vector / RAG implementation)                                                                                        | 戴睿真           | 欉家誼、蕭彤恩              | seed_vectors.py, policy JSON integration, embeddings, vector similarity retrieval |

### Design Document

| Section                                     | Primary Author | Supporting Member(s) | Notes |
| ------------------------------------------- | -------------- | -------------------- | ----- |
| Section 1 — ER Diagram                      | 欉家誼            |                      |       |
| Section 2 — Normalisation Justification     | 欉家誼            |                      |       |
| Section 3 — Graph Database Design Rationale | 蕭彤恩            |                      |       |
| Section 4 — Vector / RAG Design             | 戴睿真            |                      |       |
| Section 5 — AI Tool Usage Evidence          | All            |                      |       |
| Section 6 — Reflection & Trade-offs         | All            |                      |       |
| Section 7 — Optional Extension              | 戴睿真            | 蕭彤恩                  |       |

---

## 3. Estimated Contribution Percentages

| Member | Estimated % | Brief Justification                                                                                                                |
| ------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 欉家誼    | 40%         | Led relational database schema design, PostgreSQL query implementation, data seeding, ER diagram, and normalisation documentation. |
| 蕭彤恩    | 30%         | Led Neo4j graph database design, seeding scripts, and graph query implementation.                                                  |
| 戴睿真    | 30%         | Led Vector/RAG implementation and supported relational and graph database integration, query review, and AI agent coordination.    |
| Total  | 100%        |                                                                                                                                    |


## 4. Mid-Project Changes

| Change     | Original Plan | Revised Plan | Reason |
| ---------- | ------------- | ------------ | ------ |
| No changes | N/A           | N/A          | N/A    |

---

## 5. Team Declaration

We confirm that this work allocation accurately reflects how responsibilities were divided within our team.

| Name | Signature / Typed Name | Date       |
| ---- | ---------------------- | ---------- |
| 戴睿真  | 戴睿真                    | 2026-06-04 |
| 蕭彤恩  | 蕭彤恩                    | 2026-06-04 |
| 欉家誼  | 欉家誼                    | 2026-06-04 |
