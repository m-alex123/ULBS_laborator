# API & HTTP Routes — P23 Ethical Sneaker Price Monitor

> Contract specification for the FastAPI web application (`app/main.py`).
> Corresponding ledger contracts: `C-001`, `C-002`, `C-003`, `C-007`, `C-008`, `C-009`, `C-010`, `C-011` in [docs/agents/CONTRACTS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/CONTRACTS.md).

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

---

## 4. Public Guest Catalog, Registration & DS-03 Product Detail (`C-007`)

### `GET /register` and `POST /register`
- **Auth:** Public (redirects `303 -> /watchlist` if already logged in).
- **Behavior:** `POST /register` enforces CSRF (`verify_csrf_request`), validates email format and password length (`>= 12` characters, `<= 72` UTF-8 bytes), rejects duplicate emails with `409 Conflict`, hashes password with `bcrypt`, creates `User(role="user")`, sets `HttpOnly` session cookie, and redirects `303` → `/watchlist`.

### `GET /catalog`
- **Auth:** Public read-only (`get_current_user` optional).
- **Query Parameters:** `q`, `store`, `sort` (same filter/sort semantics as `/watchlist`).
- **Response:** `200 OK` (`text/html`) displaying all active `CanonicalProduct` cards, Guest read-only indicator (`MOD VIZITATOR · READ-ONLY`) + `/login` and `/register` links when unauthenticated, and links to `/products/{canonical_id}`.

### `GET /products/{canonical_id}` (`DS-03`)
- **Auth:** Public read-only (`get_current_user` optional).
- **Responses:**
  - `200 OK` (`text/html`): Side-by-side comparison across `jdsports.ro`, `sizeer.ro`, and `buzzsneakers.ro`, Chart.js + chronological history table strictly excluding `PriceHistory` rows with `status != 'valid'`, plus authenticated target-price/remove controls (or Guest login/register CTA).
  - `404 Not Found` if `canonical_id` does not exist.

---

## 5. Watchlist URL Ingestion & Mutations (`C-008`)

### `POST /watchlist`
- **Auth & CSRF:** Required (`require_user`, `verify_csrf_request`; guests redirect `303 -> /login`).
- **Form Fields:** `url` (supported `jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro` product URL), `target_price` (optional RON decimal).
- **Responses:** `303 -> /watchlist` on success; `400 Bad Request` re-rendering `watchlist.html` with error banner on unsupported domain, invalid URL, politeness refusal, or drift rejection.

### `POST /watchlist/{canonical_id}/target` & `POST /watchlist/{canonical_id}/delete`
- **Auth & CSRF:** Required (`require_user`, `verify_csrf_request`; guests redirect `303 -> /login`).
- **Behavior:** Updates `target_price` (`303 -> /products/{canonical_id}`) or removes the user's `WatchlistItem` (`303 -> /watchlist`).

---

## 6. User Notification & Profile Settings (`DS-04`, `C-010`)

### `GET /settings`
- **Auth:** Required (`require_user`, redirects `303 -> /login` for guests).
- **Response:** `200 OK` (`text/html`) rendering `DS-04` with `User` email/role, Email & Telegram toggles, `telegram_chat_id`, pairing instructions, and recent `NotificationLog` rows.

### `POST /settings/notifications`
- **Auth & CSRF:** Required (`require_user`, `verify_csrf_request`).
- **Form Fields:** `action` (`save` | `test`), `email_enabled`, `telegram_enabled`, `telegram_chat_id`.
- **Behavior:** Saves user notification toggles (and syncs user's `WatchlistItem` channel flags); when `action=test`, triggers safe test delivery or preview notice when SMTP/Telegram tokens are unconfigured.

---

## 7. Admin Scraper Health & SKU Deduplication (`DS-05`, `C-011`)

### `GET /admin`
- **Auth:** Required (`require_admin_ssr`: `303 -> /login` for guests, `403 Forbidden` for `role="user"`).
- **Query Parameters:** `snapshot_id` (optional `AdapterRunLog.id` to display escaped HTML snapshot preview).
- **Response:** `200 OK` (`text/html`) rendering `DS-05` adapter health cards, consecutive failure counts, recent `AdapterRunLog` entries, and uncertain `ProductListing` SKU match queue.

### `GET /admin/snapshots/{log_id}`
- **Auth:** Required (`require_admin_ssr`).
- **Response:** `200 OK` (`text/plain`) serving the snapshot HTML strictly from `SNAPSHOTS_DIR`, or `404` if missing/outside directory.

### `POST /admin/adapters/{store}/reset` & `POST /admin/deduplication/{listing_id}/{confirm|reject}`
- **Auth & CSRF:** Required (`require_admin_ssr`, `verify_csrf_request`).
- **Behavior:** Resets `SiteConfig.adapter_status = "healthy"` and `circuit_breaker_open = False`, or merges/rejects uncertain `ProductListing` SKU matches safely under `uq_listing_product_store` (`303 -> /admin`).
