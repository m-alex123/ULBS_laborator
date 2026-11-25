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

## Phase 3 · Ethical Scraping Adapters & Polite Polling (Step 3)
- [ ] `robots.txt` fetcher & 24h local cache using `urllib.robotparser` (`app/scrapers/robots.py`)
- [ ] Per-domain rate limiter (`delay >= 10s`, `<= 30 req/hour`) & transparent `User-Agent` HTTP client (`app/scrapers/client.py`)
- [ ] Store adapters with HTML fixtures & pytest suites:
  - [ ] `jdsports.ro` adapter (`app/scrapers/jdsports.py`)
  - [ ] `sizeer.ro` adapter (`app/scrapers/sizeer.py`)
  - [ ] `buzzsneakers.ro` adapter (`app/scrapers/buzzsneakers.py`)
- [ ] `POST /watchlist` URL ingestion & SKU deduplication workflow

## Phase 4 · Drift Detection, Snapshots & Admin Dashboard (Step 4)
- [ ] Drift detection engine (`>70%` drop, `>200%` rise, `<50 RON`, title similarity `<60%`, missing fields)
- [ ] Circuit breaker state transitions & HTML snapshot persistence in `storage/snapshots/`
- [ ] `DS-05` Admin Health Dashboard (`/admin`) with snapshot viewer, manual rescan trigger, and polling config editor

## Phase 5 · Product Detail, Settings & Alerts (Step 5)
- [ ] `DS-03` Product Detail & Chart.js price history (`/products/{sku}`)
- [ ] `DS-04` Notification & Profile Settings (`/settings`)
- [ ] Email (SMTP) and Telegram Bot notification dispatchers + `NotificationLog` persistence

## Phase 6 · Final Delivery & Deployment (Step 6)
- [ ] End-to-end tests covering scraping → drift → alert pipeline
- [ ] Production deployment verification (`PORT` binding, PostgreSQL 16, `ENVIRONMENT=production` secret validation)
- [ ] Final lab submission checklist & demo walkthrough
