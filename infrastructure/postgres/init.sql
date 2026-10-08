-- ==============================================================================
-- SevaHealth AI PostgreSQL Initialization Script
-- Bootstraps complete clinical domain model schema & index architecture
-- ==============================================================================

\i /docker-entrypoint-initdb.d/migrations/001_initial_domain_model.sql
