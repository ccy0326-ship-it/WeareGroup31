# Task 6 Extension: Graph Route Intelligence and Repeatable RAG Seeding

## Motivation

The original agent could call graph and policy-search tools, but several graph route functions were still placeholders and vector reseeding could create duplicate policy documents. This extension makes route planning demonstrable in the live app and makes the RAG policy index easier to rebuild reliably during demos.

## Modified Files

### `databases/graph/queries.py`

Task 6 comment added near the top of the file.

New or expanded functions:

- `_relationship_pattern(network, origin_id, destination_id)`
  - Infers whether a route should use metro, rail, or the full cross-network graph.
  - Database operation supported: selects the Cypher relationship types used by later Neo4j path queries.

- `_route_query(weight_expr, rel_pattern)`
  - Builds the reusable Cypher query for path search.
  - Database operation supported: reads Neo4j `Station` nodes and route relationships, returning path nodes, relationship legs, travel time, and fare fields.

- `_route_from_record(record, origin_id, destination_id, total_key)`
  - Converts a Neo4j record into the structured dictionary format expected by the agent.

- `query_shortest_route(origin_id, destination_id, network)`
  - Finds the fastest route using `travel_time_min` on graph relationships.
  - Database operation: Neo4j path query across `METRO_LINK`, `RAIL_LINK`, `RAIL_EXPRESS_LINK`, and/or `INTERCHANGE`.

- `query_cheapest_route(origin_id, destination_id, network, fare_class)`
  - Finds the lowest estimated fare route using `fare_usd`, `fare_standard_usd`, and `fare_first_usd`.
  - Database operation: Neo4j path query ordered by relationship fare properties.

- `query_alternative_routes(origin_id, destination_id, avoid_station_id, network, max_routes)`
  - Returns alternative routes that avoid a disrupted station.
  - Database operation: Neo4j path query with a station-exclusion condition.

- `query_interchange_path(origin_id, destination_id)`
  - Returns a richer cross-network path between metro and national rail stations.
  - Database operation: Neo4j path query including `INTERCHANGE` relationships and detailed route legs.

- `query_delay_ripple(delayed_station_id, hops)`
  - Uses the requested hop count instead of a fixed two-hop search.
  - Database operation: Neo4j variable-length traversal from the delayed station.

### `skeleton/agent.py`

Task 6 comment added near the top of the file.

New or expanded functions and logic:

- `_format_task6_graph_answer(tool_name, result_json)`
  - Formats graph and policy-search outputs directly from database JSON.
  - Prevents the LLM from guessing or rewriting route, delay-ripple, and RAG policy data incorrectly.

- Deterministic delay-ripple fallback in `run_agent(...)`
  - Routes disruption-impact questions such as `Which stations are affected if NR03 is delayed within 3 hops?` to `get_delay_ripple`.
  - Keeps delay-ripple questions separate from refund and compensation policy questions.

- Deterministic policy/RAG fallback in `run_agent(...)`
  - Routes refund, day-pass, ticket-type, luggage, and conduct questions to `search_policy`.
  - Overrides accidental fare or route selections from small local models.

Database operations supported:

- Calls existing Neo4j-backed tools through `_execute_tool(...)`, then returns visible, correct output from the retrieved DB result.

### `skeleton/seed_neo4j.py`

Task 6 comment added near the top of the file.

New seed data added to graph relationships:

- `METRO_LINK.fare_usd`
  - Loaded from `train-mock-data/metro_schedules.json`.

- `RAIL_LINK.fare_standard_usd`
  - Loaded from normal national rail schedule fare classes.

- `RAIL_LINK.fare_first_usd`
  - Loaded from normal national rail schedule fare classes.

- `RAIL_EXPRESS_LINK`
  - New graph relationship created from express services in `train-mock-data/national_rail_schedules.json`.
  - Includes `schedule_id`, `line`, `service_type`, `travel_time_min`, `fare_standard_usd`, and `fare_first_usd`.

- `INTERCHANGE.fare_usd`
  - Set to `0.0` so cross-network transfer links do not add ticket fare.

### `skeleton/seed_vectors.py`

Task 6 comment added near the top of the file.

New behavior:

- Calls `clear_policy_documents()` before inserting policy vectors.
- Prints clearer guidance when an embedding dimension mismatch occurs.

Database operation:

- Rebuilds the PostgreSQL `policy_documents` vector index from the latest policy JSON files without duplicate rows.

### `databases/relational/queries.py`

Task 6 comment added near the top of the file.

New function:

- `clear_policy_documents()`
  - Deletes existing rows from PostgreSQL `policy_documents` before reseeding.
  - Database operation: `DELETE FROM policy_documents`.

## Example Queries for Demo

After starting Docker and reseeding Neo4j:

```bash
python3 skeleton/seed_neo4j.py
```

Run these in the Gradio UI:

- `What is the fastest route from MS01 to MS14?`
- `What is the cheapest route from NR01 to NR05?`
- `Find alternative routes from MS01 to MS14 avoiding MS04.`
- `Find a route from MS01 to NR05.`
- `Which stations are affected if NR03 is delayed within 3 hops?`

After reseeding policy vectors:

```bash
python3 skeleton/seed_vectors.py
```

Run these in the Gradio UI:

- `What ticket types are available?`
- `Can I refund a metro day pass?`
- `What luggage can I bring on national rail?`

## Testing Evidence to Capture

- Screenshot of `python3 skeleton/seed_neo4j.py` completing successfully.
- Screenshot of `python3 skeleton/seed_vectors.py` completing successfully.
- Screenshot of the Gradio UI answering one fastest-route query.
- Screenshot of the Gradio UI answering one station-avoidance query, for example `MS01` to `MS14` avoiding `MS04`.
- Screenshot of the Gradio UI answering one delay-ripple query, for example `NR03` delayed within `3` hops.
- Screenshot of the Gradio UI answering one policy/RAG query.

## Integration Notes

- Existing agent tool names were preserved, while `skeleton/agent.py` now adds deterministic fallbacks and formatting for the Task 6 graph tools.
- Original relational booking and fare functions are unchanged.
- The graph extension is demonstrable either through the Gradio UI or by directly calling the functions in `databases/graph/queries.py`.
