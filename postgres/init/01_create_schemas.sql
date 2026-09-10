-- raw: landing zone for Spark-loaded Silver data (Stage 5 loader writes here)
-- analytics: dbt-built staging/intermediate/marts models (Stage 5 dbt project)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;
