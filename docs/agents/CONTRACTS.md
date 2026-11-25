# Contracts — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> Promises across a boundary. **Provided:** this repo owns the contract; the text
> lives here only. **Consumed:** a link to the provider's entry plus the fields this
> repo relies on. **External:** what we rely on from a third-party service.
> Changing a provided contract is a PROPOSAL (AGENTS.md → The gate) and the plan
> lists the consumers' files too. Status: `approved` · `proposed` · `superseded-by`.
<!-- graffino-agentic:end -->

## Index
- C-001 · Health Check Endpoint Contract · provided
- C-002 · Server-Side Session Authentication & Role Enforcement Contract · provided
- C-003 · Live Watchlist SSR Query & View Contract · provided

---

## Provided

### C-001 · Health Check Endpoint Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `GET /health` executes `SELECT 1` against the configured SQLAlchemy session (`check_db_connection`) and returns `200 {"status": "ok", "database": "ok"}` when healthy or `503 {"status": "error", "database": "unreachable"}` on database failure.
- **Evidence:** Implemented in [app/web/routers/health.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/health.py), documented in [API.md](file:///home/manol/Work/ULBS_laborator/API.md), and tested in [tests/test_health.py](file:///home/manol/Work/ULBS_laborator/tests/test_health.py).

### C-002 · Server-Side Session Authentication & Role Enforcement Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `GET /login` (`DS-01`), `POST /login` (verifies `email` + `password` via `bcrypt`, sets HMAC-SHA256 signed `HttpOnly` `SameSite=Lax` cookie `p23_session` and redirects `303` to `/watchlist`, or returns `401`), `POST /logout` (clears cookie and redirects `303` to `/login`), and `require_user` / `require_admin` dependencies enforcing `user` vs `admin` roles (`401`/`403` on `GET /admin/status`).
- **Evidence:** Implemented in [app/core/security.py](file:///home/manol/Work/ULBS_laborator/app/core/security.py), [app/web/deps.py](file:///home/manol/Work/ULBS_laborator/app/web/deps.py), and [app/web/routers/auth.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/auth.py); documented in [API.md](file:///home/manol/Work/ULBS_laborator/API.md); tested in [tests/test_auth.py](file:///home/manol/Work/ULBS_laborator/tests/test_auth.py).

### C-003 · Live Watchlist SSR Query & View Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `GET /` and `GET /watchlist` (authenticated via `require_user`, accepting `?q=&store=&sort=`) query `WatchlistItem`, `CanonicalProduct`, `ProductListing`, `PriceHistory`, and `SiteConfig`, rendering `DS-02` with real product photos (`object-fit: contain`), retailer & source badges, offline SVG fallback, sparkline trends, circuit breaker banner, and empty state.
- **Evidence:** Implemented in [app/services/watchlist_service.py](file:///home/manol/Work/ULBS_laborator/app/services/watchlist_service.py) and [app/web/routers/watchlist.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/watchlist.py); documented in [API.md](file:///home/manol/Work/ULBS_laborator/API.md); tested in [tests/test_watchlist.py](file:///home/manol/Work/ULBS_laborator/tests/test_watchlist.py).

## Consumed

## External
