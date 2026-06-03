# Database Deployment Runbook

## Empty Database

1. Create a Supabase project.
2. Open the SQL editor.
3. Run `backend/sql/production_readiness.sql`.
4. Create the first platform admin in Supabase Auth.
5. Insert the database role for that user:

```sql
insert into public.profiles (id, email, role, full_name)
values (
  'AUTH_USER_UUID',
  'admin@example.com',
  'super',
  'Platform Admin'
);
```

The application trusts the `public.profiles.role` value only.

## Existing Database

1. Take a Supabase backup before migration:

```bash
supabase db dump --db-url "$SUPABASE_DB_URL" --file "backup-before-security-hardening.sql"
```

2. Run `backend/sql/production_readiness.sql`.
3. Verify RLS and indexes:

```sql
select * from public.qr_menu_rls_audit;
select * from public.qr_menu_policy_audit;
select * from public.qr_menu_required_index_audit;
select * from public.qr_menu_tenant_isolation_audit;
```

4. Confirm every row in `qr_menu_rls_audit` has `rls_enabled = true` and `rls_forced = true`.
5. Confirm every row in `qr_menu_required_index_audit` has `exists_in_database = true`.
6. Confirm every row in `qr_menu_tenant_isolation_audit` has `unsafe_rows = 0`.

## Production Environment

Set these backend variables before deploying hardened code:

```bash
ENVIRONMENT=production
BACKEND_CORS_ORIGINS=https://your-frontend.example.com
BACKEND_ALLOWED_HOSTS=your-backend.example.com
RATE_LIMIT_STORAGE_URL=redis://your-redis-host:6379/0
SENTRY_DSN=https://your-sentry-dsn
SENTRY_TRACES_SAMPLE_RATE=0.1
```

`BACKEND_CORS_ORIGINS` should be set before sending real browser traffic.
Production startup does not fail if it is missing because failed health checks
make deploy recovery harder, but the API then uses an empty CORS allow-list.
That means non-browser clients and Render health checks continue to work while
browser calls from the frontend remain blocked until explicit origins are set.

On Render, `BACKEND_ALLOWED_HOSTS` can be left blank when using the default
`onrender.com` backend URL because the app trusts Render's
`RENDER_EXTERNAL_HOSTNAME` automatically. Set `BACKEND_ALLOWED_HOSTS` explicitly
when using a custom API domain; the default Render hostname remains trusted
automatically. Never set it to `*` in production.

Do not set `BACKEND_CORS_ORIGIN_REGEX` in production. If it is present, the
backend logs a warning and ignores it because production CORS must use exact
frontend origins. Do not use `*`; wildcard origins are ignored in production.

`RATE_LIMIT_STORAGE_URL` is recommended before scaling beyond one instance or
accepting meaningful production traffic. If it is missing, the API still boots
with in-memory rate limits and logs a high-severity warning so starter Render
deploys can pass health checks.

## Rollback

1. Pause writes by disabling dashboard access or putting the backend in maintenance mode.
2. Restore the database backup if data shape rollback is required:

```bash
psql "$SUPABASE_DB_URL" < backup-before-security-hardening.sql
```

3. If only policy rollback is required, run `backend/sql/rollback_security_hardening.sql`.
4. Redeploy the previous backend build.
5. Re-enable writes after login, menu reads, owner dashboard, and super dashboard are verified.

## Attack Scenarios Blocked

- Owner changes `user_metadata.role` or JWT claims to `super`: ignored by API and RLS helper functions.
- Owner queries another restaurant ID: RLS owner policies require `restaurants.owner_id = auth.uid()`.
- Owner creates a menu item under another restaurant/category pair: RLS and the category/restaurant foreign key reject it.
- Anonymous browser directly queries Supabase tables: anon grants are revoked and no anon table policies exist.
- Hard delete by authenticated clients: table delete policies are absent and hard-delete triggers reject deletes.
- Deleted categories/items appearing in public menus: public queries and RPC require `deleted_at is null`.
