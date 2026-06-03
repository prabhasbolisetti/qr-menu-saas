# QR Menu SaaS

A production-ready QR menu platform for restaurants. Platform admins onboard restaurants and owners, owners manage menu categories/items/availability, and guests scan a permanent QR code to view a fast mobile menu.

## What is included

- Public mobile menu at `/menu/:slug`
- Super admin dashboard for restaurant onboarding
- Owner dashboard for menu operations
- Supabase Auth with `super` and `owner` roles
- Supabase Postgres data model with production hardening SQL
- Cloudinary image upload for menu items
- Permanent QR generation per restaurant
- Vercel-ready frontend and Render-ready FastAPI backend

## Tech stack

- Frontend: React, Vite, Tailwind CSS, React Router, Axios
- Backend: FastAPI, Pydantic, Supabase Python SDK
- Services: Supabase Auth/Postgres, Cloudinary, QR Server API

## Project structure

```text
backend/
  app/
    routers/       FastAPI route modules
    services/      Supabase, QR, image, and menu logic
    schemas/       Pydantic request models
  sql/             Production database migration
frontend/
  src/
    pages/         Public menu and dashboard screens
    components/    Shared UI components
    api/           Axios client
```

## Local setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Fill `backend/.env` with Supabase and Cloudinary credentials before starting.
For production, set `ENVIRONMENT=production`, keep the Supabase service role
key only on the backend host, and restrict `BACKEND_ALLOWED_HOSTS` to your API
domain when using a custom backend domain.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000` for local backend development.

## Database setup

Run the SQL in `backend/sql/production_readiness.sql` in the Supabase SQL editor. It creates or upgrades the schema, enables RLS, adds tenant policies, audit logging, soft deletes, indexes, constraints, and public menu RPC support.

After the schema is ready, create at least one platform admin in Supabase Auth, then insert the database role in `public.profiles`:

```sql
insert into public.profiles (id, email, role, full_name)
values ('AUTH_USER_UUID', 'admin@example.com', 'super', 'Platform Admin');
```

Then log in at `/login` and onboard restaurants from the platform admin dashboard.

## Deployment

### Frontend on Vercel

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://your-backend.example.com`

### Backend on Render

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add all variables from `backend/.env.example`

Set `FRONTEND_PUBLIC_BASE_URL` to the deployed frontend URL so generated QR codes point at the live menu.
Set `BACKEND_CORS_ORIGINS` to the deployed frontend URL.
On Render, `BACKEND_ALLOWED_HOSTS` can be left blank for the default
`onrender.com` backend host because the API uses Render's
`RENDER_EXTERNAL_HOSTNAME` automatically. If you attach a custom API domain, set
`BACKEND_ALLOWED_HOSTS` to that backend host, for example `api.yourdomain.com`;
the default Render hostname remains trusted automatically.
Set `RATE_LIMIT_STORAGE_URL` to a Redis URL before scaling beyond a single
starter instance or accepting meaningful production traffic. If it is missing,
the API still boots with in-memory rate limits and logs a high-severity warning.
Set `SENTRY_DSN` to enable production error tracking and request tracing.

## Useful commands

```bash
cd frontend && npm run lint
cd frontend && npm run build
backend/venv/bin/python -m compileall backend/app
```

## Sellable feature checklist

- Restaurant onboarding creates owner account, restaurant, role profile, and QR code.
- Owners can add, edit, hide, and delete menu items.
- Public menu supports categories, item photos, veg/non-veg markers, specials, bestsellers, MRP pricing, open/closed state, and mobile sticky navigation.
- Hidden menu items stay out of the public menu.
- Backend validates required environment values at startup and adds security headers in production.
- Image uploads are restricted to real JPEG/PNG/WebP images and capped by `MAX_IMAGE_UPLOAD_MB`.
- Database migration protects owner/category/item relationships, slug uniqueness, RLS tenant isolation, soft deletes, and audit logging.
- Deployment templates and environment examples are included.
