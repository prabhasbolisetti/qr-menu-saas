# Seller Handoff

Use this file when handing the project to a buyer, client, or deployment operator.

## Demo flow

1. Log in as a platform admin.
2. Create a restaurant with owner email, temporary password, name, city, and slug.
3. Open the restaurant detail page and download the generated QR code.
4. Add categories and menu items, including image URLs or uploads.
5. Toggle open/closed and item availability.
6. Scan or open the public menu URL.
7. Log in as the owner and confirm they can manage only their restaurant.

## Required services

- Supabase project with Auth enabled
- Supabase SQL migration from `backend/sql/production_readiness.sql`
- Cloudinary account for image upload
- Frontend host such as Vercel
- Backend host such as Render

## Production checks

- `ENVIRONMENT=production` is set on the backend host.
- `FRONTEND_PUBLIC_BASE_URL` points to the real frontend domain.
- `BACKEND_CORS_ORIGINS` includes the production frontend domain.
- `BACKEND_ALLOWED_HOSTS` includes the backend host when using a custom API domain, for example `api.yourdomain.com`. On Render's default `onrender.com` backend URL, it can be left blank because Render provides the host automatically.
- Supabase service role key is stored only on the backend host.
- Cloudinary upload folder and max image size are configured for client use.
- A `super` admin account exists before client handoff.
- QR code scans open the deployed domain, not localhost.
- Public menu loads without authentication.
- Hidden/unavailable items do not appear on the public menu.
- Owner dashboard rejects non-owner accounts.

## Buyer acceptance test

Run these before marking the project ready to sell:

```bash
cd frontend && npm run lint
cd frontend && npm run build
python3 -m compileall backend/app
```

Then deploy and confirm:

1. `/health` returns `healthy` with `environment=production`.
2. Public menu URLs load from the production frontend domain.
3. Image uploads reject non-image files and files larger than `MAX_IMAGE_UPLOAD_MB`.
4. Owner accounts cannot access `/super`.
5. Super admin can onboard a restaurant, download the QR, and the QR opens the deployed menu.
