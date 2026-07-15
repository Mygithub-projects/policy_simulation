HISTORICAL BACKUP DATABASE FILE.

This folder contains the original DuckDB database file used before migration to PostgreSQL.
The running application now uses PostgreSQL (`localhost:5432`, database `workforce_policy_agent`).

The .duckdb file is retained as a migration-source backup and historical reference — it is no longer read by the running application.

Expected extension: .duckdb
File example: workforce_policy_agent_preclean_20260619_144113.duckdb

Do not delete this file.
