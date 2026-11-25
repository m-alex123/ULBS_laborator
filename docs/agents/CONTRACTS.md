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
- C-004 · Polite HTTP Client & robots.txt Enforcement Contract · provided
- C-005 · Store Adapter & Pure Price Parser Contract · provided
- C-006 · Drift Detection, Snapshot Persistence & Cross-Site Deduplication Contract · provided

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

### C-004 · Polite HTTP Client & robots.txt Enforcement Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `PoliteHttpClient.fetch(url, *, min_delay_seconds=None, max_requests_per_hour=None, circuit_breaker_open=False)` sends `settings.USER_AGENT`, validates cached (24h TTL) `robots.txt` via `urllib.robotparser.RobotFileParser` combined with RFC-9309 `*`/`$` wildcard rules (fail-closed on non-200 or HTML responses), enforces `>=10s` per-domain delay and `<=30 req/h` sliding window, checks `circuit_breaker_open`, and raises typed `PoliteClientError` subclasses (`RobotsDisallowedError`, `HourlyRateLimitExceededError`, `CircuitBreakerOpenError`, `UpstreamFetchError`).
- **Evidence:** Implemented in [app/scraping/polite_client.py](file:///home/manol/Work/ULBS_laborator/app/scraping/polite_client.py) and tested offline in [tests/test_polite_client.py](file:///home/manol/Work/ULBS_laborator/tests/test_polite_client.py).

### C-005 · Store Adapter & Pure Price Parser Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `parse_price_text`, `parse_price_info`, `parse_price_pair_from_text`, and `parse_availability` parse Romanian prices and stock labels side-effect-free into `ParsedPriceInfo` (`Decimal | None`, `currency="RON"`) and `bool | None`; `get_adapter(store)` / `get_adapter_for_url(url)` resolve `JDSportsAdapter`, `SizeerAdapter`, and `BuzzSneakersAdapter`, whose `parse(html, url)` returns `ScrapedProductData`.
- **Evidence:** Implemented in [app/scraping/price_parser.py](file:///home/manol/Work/ULBS_laborator/app/scraping/price_parser.py) and [app/scraping/adapters/](file:///home/manol/Work/ULBS_laborator/app/scraping/adapters/__init__.py); tested offline in [tests/test_price_parser.py](file:///home/manol/Work/ULBS_laborator/tests/test_price_parser.py) and [tests/test_adapters.py](file:///home/manol/Work/ULBS_laborator/tests/test_adapters.py).

### C-006 · Drift Detection, Snapshot Persistence & Cross-Site Deduplication Contract
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Interface:** `check_plausibility` and `record_scrape_outcome` enforce `D-002` thresholds (`>70%` drop, `>200%` rise, `<50 RON`, title similarity `<60%`, missing required fields), mark `SiteConfig.adapter_status = 'suspect'` and `AdapterRunLog(status='suspect')`, save HTML snapshots in `storage/snapshots/`, preserve last valid `ProductListing` values, and return `should_notify_users=False` on drift/error; `resolve_canonical_product` and `upsert_scraped_listing` normalize SKUs across retailers and flag uncertain fuzzy matches via `ProductListing.match_needs_review=True` and `suggested_canonical_product_id`.
- **Evidence:** Implemented in [app/scraping/drift_detector.py](file:///home/manol/Work/ULBS_laborator/app/scraping/drift_detector.py) and [app/scraping/deduplicator.py](file:///home/manol/Work/ULBS_laborator/app/scraping/deduplicator.py); tested in [tests/test_drift_detector.py](file:///home/manol/Work/ULBS_laborator/tests/test_drift_detector.py) and [tests/test_deduplicator.py](file:///home/manol/Work/ULBS_laborator/tests/test_deduplicator.py).

## Consumed

## External
