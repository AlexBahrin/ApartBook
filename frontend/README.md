# ApartBook — Vue 3 SPA + Django REST API

The frontend has been ported from Django templates to a **Vue 3 single-page app**
(Vite) that talks to a **Django REST Framework** JSON API using **JWT** auth.

## Architecture

```
frontend/        Vue 3 + Vite SPA (Pinia, Vue Router, vue-i18n, axios)
Apartament/
  api/           DRF app: serializers, viewsets, JWT auth, all endpoints (/api/…)
  app/           Existing domain models / business logic (unchanged)
  authentication/ User model extensions (UserProfile)
```

- **Auth:** `POST /api/auth/login/` returns `{ access, refresh, user }` (SimpleJWT).
  The access token is sent as `Authorization: Bearer <token>`; the axios client
  auto-refreshes on 401.
- **Legacy Django template pages** remain routed under `/<lang>/…` for backward
  compatibility, but the Vue SPA is now the primary frontend.

## Development

Two processes:

1. **Backend** (Django, port 8000):
   ```bash
   .venv/bin/python Apartament/manage.py runserver
   ```
2. **Frontend** (Vite dev server, port 5173):
   ```bash
   cd frontend
   npm install      # first time only
   npm run dev
   ```
   Open http://localhost:5173 — the Vite dev server proxies `/api` and `/media`
   to Django, so there are no CORS issues.

## Production (Django serves the built SPA)

```bash
cd frontend
npm run build           # outputs to frontend/dist, base=/static/spa/
```

Then Django serves:
- the SPA entry (`index.html`) at `/` and any client-side route (catch-all),
- the built assets under `/static/spa/…` (via `STATICFILES_DIRS`).

Run `collectstatic` as usual for your production static setup.

## API overview

| Area | Endpoint |
|------|----------|
| Config (currencies, languages) | `GET /api/config/` |
| Login / refresh | `POST /api/auth/login/`, `POST /api/auth/refresh/` |
| Register / activate | `POST /api/auth/register/`, `POST /api/auth/activate/` |
| Password reset | `POST /api/auth/password-reset/`, `.../confirm/` |
| Current user | `GET/PATCH /api/auth/me/` |
| Public apartments | `GET /api/apartments/`, `/api/apartments/{slug}/` |
| Availability / price | `/api/apartments/{slug}/availability/`, `/price/` |
| My bookings | `/api/my/bookings/` (+ `create-for/{slug}/`, `{id}/cancel/`) |
| My conversations | `/api/my/conversations/` (+ `start/{bookingId}/`, `{id}/send/`) |
| Staff apartments | `/api/staff/apartments/` (+ images, availability, ical, calendar) |
| Staff bookings | `/api/staff/bookings/` (+ `{id}/status/`, `{id}/edit/`) |
| Staff conversations | `/api/staff/conversations/` |
| Staff global calendar | `/api/staff/calendar-events/` |

## i18n

English and Romanian translations are included in `frontend/src/i18n/`.
The other five languages (ru, uk, de, fr, es) currently fall back to English —
add message files and register them in `frontend/src/i18n/index.js` to complete them.
