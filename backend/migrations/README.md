# Database migrations

Apply in numeric order. Each file is idempotent-safe to read but NOT to re-run.

## Apply against Supabase (production / staging)

1. Open Supabase Dashboard → SQL Editor.
2. Paste contents of each `.sql` file in order:
   - `001_initial_schema.sql`
   - `002_rls_policies.sql`
3. Run.

## Future migrations

New files: `003_<short_name>.sql`, `004_<short_name>.sql`, etc. Never edit applied files — write a follow-up migration instead.
