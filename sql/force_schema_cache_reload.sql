-- Force PostgREST to reload its schema cache
-- Run this whenever you add columns but the API returns "Could not find column in schema cache"
NOTIFY pgrst, 'reload config';
