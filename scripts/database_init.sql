-- 1. Create the Read-Only User if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT * FROM pg_catalog.pg_user WHERE usename = 'read_only_user') THEN
        CREATE USER read_only_user WITH PASSWORD 'read_only_pass';
    END IF;
END
$$;