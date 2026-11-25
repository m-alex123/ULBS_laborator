# TODO — P23 Ethical Sneaker Price Monitor

> Tracking backlog from foundation through Checkpoint and Final Delivery.

## Phase 1 · Foundation (Step 1) — Done
- [x] Project scope, ethical analysis, and user interview ([docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md), [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md), [INTERVIEW.md](file:///home/manol/Work/ULBS_laborator/INTERVIEW.md))
- [x] Design tokens & `DS-02` HTML mock ([docs/design/DESIGN.md](file:///home/manol/Work/ULBS_laborator/docs/design/DESIGN.md), [ds-02-watchlist.html](file:///home/manol/Work/ULBS_laborator/docs/design/mocks/ds-02-watchlist.html))
- [x] SQLAlchemy 2.0 schema (8 models: `User`, `CanonicalProduct`, `ProductListing`, `PriceHistory`, `WatchlistItem`, `AdapterRunLog`, `SiteConfig`, `NotificationLog`)
- [x] `bcrypt` password hashing (`app/core/security.py`) and idempotent seed (`app/db/seed.py`)
- [x] 24 foundation unit/integration tests (`tests/test_models.py`, `tests/test_security.py`, `tests/test_seed.py`)

## Phase 2 · Checkpoint Core (Step 2) — In Progress / Current Milestone
- [x] Real sneaker product photos in `DS-02` mock and `app/db/seed.py` with `object-fit: contain`, retailer attribution, and offline fallback
- [x] PostgreSQL 16 (`psycopg`) support alongside SQLite (`app/db/session.py`, `requirements.txt`)
- [x] Local Docker Compose stack (`Dockerfile` with `${PORT:-8000}` + `docker-compose.yml` with PostgreSQL 16 healthcheck)
- [x] GitHub Actions CI workflow (`.github/workflows/ci.yml`: `pytest -v` + `ledger-lint.py`)
- [x] `GET /health` DB readiness endpoint (`app/web/routers/health.py`)
- [x] Server-side session auth (`GET/POST /login`, `POST /logout`) with HMAC-SHA256 `HttpOnly` cookies and `user`/`admin` role enforcement (`GET /admin/status`)
- [x] SSR `DS-01` Login and `DS-02` Live Watchlist (`GET /`, `GET /watchlist`) with search, store chips, sort, CB banner, and empty state
- [x] `API.md`, `CONTRACTS.md` (`C-001`..`C-003`), `TODO.md`, and updated `README.md`

## Phase 3 · Ethical Scraping Adapters, Drift Detection & SKU Deduplication (Step 3)
- [x] Pure Romanian price & availability parser (`app/scraping/price_parser.py`) + 26 unit tests
- [x] `robots.txt` fetcher & 24h local cache using `urllib.robotparser` + RFC-9309 wildcards, per-domain rate limiter (`delay >= 10s`, `<= 30 req/hour`), & transparent `User-Agent` HTTP client (`app/scraping/polite_client.py`)
- [x] Store adapters with offline HTML fixtures & pytest suites:
  - [x] `jdsports.ro` adapter (`app/scraping/adapters/jdsports.py`)
  - [x] `sizeer.ro` adapter (`app/scraping/adapters/sizeer.py`)
  - [x] `buzzsneakers.ro` adapter (`app/scraping/adapters/buzzsneakers.py`)
- [x] P23 Drift detection engine (`>70%` drop, `>200%` rise, `<50 RON`, title similarity `<60%`, missing fields) & HTML snapshot persistence in `storage/snapshots/` (`app/scraping/drift_detector.py`)
- [x] Cross-site SKU normalization & fuzzy deduplication engine with uncertain-match admin flag (`app/scraping/deduplicator.py`)
- [x] `POST /watchlist` URL ingestion & watchlist item mutations (`app/services/ingestion_service.py`, `app/web/routers/watchlist.py`)

## Phase 4 · Guest Mode, DS-03 Comparison, Background Worker & Admin Dashboard (Step 4)
- [x] Guest read-only catalog (`GET /catalog`), "Continue as Guest" on `/login`, and public `GET/POST /register` (`app/web/routers/catalog.py`, `auth.py`)
- [x] `DS-03` Product Detail & Chart.js cross-site price history excluding `suspect` entries (`GET /products/{canonical_id}`)
- [x] Scheduled polling worker runner & CLI `--once` entrypoint (`app/worker/runner.py`)
- [ ] `DS-05` Admin Health Dashboard (`/admin`) with snapshot viewer, uncertain-match review confirmation, manual rescan trigger, and polling config editor
- [ ] Automatic circuit breaker auto-trip transitions on consecutive upstream failures

## Phase 5 · Product Detail, Settings & Alerts (Step 5)
- [ ] `DS-03` Product Detail & Chart.js price history (`/products/{sku}`)
- [ ] `DS-04` Notification & Profile Settings (`/settings`)
- [ ] Email (SMTP) and Telegram Bot notification dispatchers + `NotificationLog` persistence

## Phase 6 · Final Delivery & Deployment (Step 6)
- [ ] End-to-end tests covering scraping → drift → alert pipeline
- [ ] Production deployment verification (`PORT` binding, PostgreSQL 16, `ENVIRONMENT=production` secret validation)
- [ ] Final lab submission checklist & demo walkthrough
