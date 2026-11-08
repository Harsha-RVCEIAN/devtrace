-- Automatically create test database alongside development database on first startup
SELECT 'CREATE DATABASE devtrace_test_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'devtrace_test_db')\gexec
