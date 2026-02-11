-- Create Grafana database if it doesn't exist
-- This database will store all Grafana metadata including:
-- - Dashboard definitions and versions
-- - User preferences and settings
-- - Alert configurations
-- - Data source configurations
-- - Organization and team settings

SELECT 'CREATE DATABASE grafanadb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'grafanadb')\gexec

-- Grant all privileges to the root user
GRANT ALL PRIVILEGES ON DATABASE grafanadb TO root;
