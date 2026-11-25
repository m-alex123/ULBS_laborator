# API & HTTP Routes — P23 Ethical Sneaker Price Monitor

> Contract specification for the FastAPI web application (`app/main.py`).
> Corresponding ledger contracts: `C-001`, `C-002`, `C-003` in [docs/agents/CONTRACTS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/CONTRACTS.md).

---

## 1. Health & Readiness (`C-001`)

### `GET /health`
- **Auth:** Public (no session cookie required).
- **Description:** Verifies application process readiness and database connectivity (`SELECT 1`). Used by Docker Compose, PaaS health probes, and CI checks.
- **Responses:**
  - `200 OK` (`application/json`):
    ```json
    {"status": "ok", "database": "ok"}
    ```
  - `503 Service Unavailable` (`application/json`):
    ```json
    {"status": "error", "database": "unreachable"}
    ```

---

## 2. Authentication & Role Enforcement (`C-002`)

Session state is stored in an `HttpOnly`, `SameSite=Lax` cookie (`SESSION_COOKIE_NAME`, default `p23_session`) containing an HMAC-SHA256 signed payload (`sub` user ID, `role`, `exp`). Passwords are verified against `users.password_hash` via `bcrypt`.

### `GET /login`
- **Auth:** Public. Authenticated visitors are redirected (`303 See Other`) to `/watchlist`.
- **Response:** `200 OK` (`text/html`) rendering `DS-01` (`app/web/templates/login.html`). In non-production environments (`ENVIRONMENT != "production"`), demo quick-fill shortcuts are rendered for `user@pricemonitor.local` and `admin@pricemonitor.local`.

### `POST /login`
- **Auth:** Public.
- **Content-Type:** `application/x-www-form-urlencoded`
- **Form Fields:**
  - `email` (string, required)
  - `password` (string, required)
- **Responses:**
  - `303 See Other` → `Location: /watchlist`, sets `Set-Cookie: p23_session=...; HttpOnly; SameSite=Lax; Path=/` (`Secure` enabled when `ENVIRONMENT=production`).
  - `401 Unauthorized` (`text/html`) → re-renders `login.html` with `Email sau parolă incorectă.`.

### `POST /logout`
- **Auth:** Public / authenticated.
- **Response:** `303 See Other` → `Location: /login`, deletes `p23_session` cookie.

### `GET /admin/status`
- **Auth:** Required (`role == "admin"` enforced server-side via `require_admin`).
- **Responses:**
  - `200 OK` (`application/json`):
    ```json
    {"status": "ok", "admin_email": "admin@pricemonitor.local", "role": "admin"}
    ```
  - `401 Unauthorized` when unauthenticated.
  - `403 Forbidden` when authenticated as `role == "user"`.

---

## 3. Live Watchlist SSR (`C-003`)

### `GET /` and `GET /watchlist`
- **Auth:** Required (`require_user`). Unauthenticated requests receive `303 See Other` → `Location: /login`.
- **Query Parameters:**
  - `q` (string, optional): Case-insensitive substring filter over `CanonicalProduct.name`, `brand`, and `sku`.
  - `store` (string, optional, default `all`): Retailer filter (`all` | `jdsports` | `sizeer` | `buzzsneakers`).
  - `sort` (string, optional, default `lowest_price`): Card ordering (`lowest_price` | `biggest_discount` | `recent`).
- **Response:** `200 OK` (`text/html`) rendering `DS-02` (`app/web/templates/watchlist.html`) with:
  - Live retailer ticker strip (`SiteConfig` & listing counts)
  - Circuit breaker alert banner when any `SiteConfig.circuit_breaker_open` is `true`
  - Sneaker cards with real HTTPS product photos (`object-fit: contain`), retailer attribution badge, photo source badge, offline SVG fallback, 2-line clamped title with tooltip, 7-point price sparkline SVG, and 3-store comparison table (`jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro`)
  - Empty state panel when no watchlist items match.
