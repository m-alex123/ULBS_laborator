# Architecture — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> How this repo is built, generated from the code at backfill and kept current by
> whoever changes the structure. The code wins: when this page is wrong, fix it.
<!-- graffino-agentic:end -->

## Overview
Proiectul P23: Monitor de prețuri cu scraping etic pentru încălțăminte sport (sneakers) pe 3 magazine partenere din România (`jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro`), cu respectarea `robots.txt`, deduplicare după SKU, detecție de derivă a adaptoarelor și alertare prin Email și Telegram.

```text
[Repository Root]
  ├── .github/workflows/ci.yml  (CI pytest + ledger-lint)
  ├── Dockerfile                (Container web Python 3.12 + seed + uvicorn)
  ├── docker-compose.yml        (PostgreSQL 16 + FastAPI web pe port 8000)
  ├── docs/                     (Cerințe, scope, decizii, contracte, design tokens)
  ├── app/                      (Cod sursă aplicație)
  │     ├── main.py             (Entrypoint FastAPI, lifespan, static, routere)
  │     ├── core/               (Configurare Pydantic Settings & securitate bcrypt/HMAC)
  │     ├── db/                 (Session SQLite/PostgreSQL, modele ORM, seed idempotent)
  │     ├── services/           (Servicii domeniu: watchlist_service.py, ingestion_service.py)
  │     ├── web/                (Routere health/auth/catalog/watchlist, deps, Jinja2, static CSS/JS)
  │     ├── scraping/           (Step 3: price_parser, polite_client, adapters/, drift_detector, deduplicator)
  │     └── worker/             (Step 4: runner.py CLI `--once` și buclă opțională de polling)
  ├── data/                     (Bază de date locală SQLite: pricemonitor.db)
  ├── storage/snapshots/        (Snapshot-uri HTML salvate la erori/derivă)
  └── tests/                    (Teste unitare, fixtures HTML și integrare pytest)
```

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| Documentation & Contracts | docs/, API.md, README.md, TODO.md | Guvernanță, specificații, decizii, contracte HTTP | Dezvoltatori, Evaluatori |
| Web Application | app/main.py, app/web/ | Rute FastAPI (`/health`, `/login`, `/register`, `/catalog`, `/products/{id}`, `/watchlist`), sesiuni `HttpOnly`, șabloane Jinja2 (`DS-01`..`DS-03`) | Utilizatori, Vizitatori Guest, Administrator |
| Domain Services | app/services/ | Agregare watchlist & catalog public, comparație `DS-03`, ingestie URL etică, sparkline, filtrare/sortare | Web App, Scraping Engine, Database |
| Security & Config | app/core/ | Setări mediu (`pydantic-settings`), hashing `bcrypt`, cookie-uri semnate HMAC-SHA256 | Web App, Database |
| Database & Models | app/db/, data/ | Modele SQLAlchemy 2.0, engine dual SQLite / PostgreSQL 16, seed idempotent | Web App, Services, Worker |
| Ethical Scraping Engine | app/scraping/ | Parser pur RO (`price_parser`), client politicos `robots.txt` (`polite_client`), adaptoare (`adapters/`), detecție derivă (`drift_detector`), deduplicare SKU (`deduplicator`) | Magazine online, Database, Storage |
| Background Worker | app/worker/runner.py | Ciclu politicos de verificare (`run_scrape_cycle`), CLI `--once`, buclă opțională controlată prin `ENABLE_BACKGROUND_WORKER` | Scraping Engine, Database |

## Data flow
1. Vizitatorii neautentificați (Guest) pot naviga catalogul public read-only (`GET /catalog`) și pagina detaliată `DS-03` (`GET /products/{canonical_id}`), iar utilizatorii autentificați își administrează Watchlist-ul (`GET/POST /watchlist`, `POST /watchlist/{id}/target`, `POST /watchlist/{id}/delete`).
2. La adăugarea unui URL nou (`POST /watchlist`) sau în ciclul worker-ului (`app/worker/runner.py`), `PoliteHttpClient` verifică `robots.txt` (cache 24h, reguli wildcard `*`/`$`), pauza `>=10s`, plafonul `<=30 req/h` și circuit breaker-ul, apoi descarcă pagina cu `User-Agent` dedicat.
3. Adaptorul specific magazinului (`jdsports`, `sizeer`, `buzzsneakers`) extrage datele normalizate folosind `price_parser` și le potrivește cross-site prin `deduplicator` (marcând potrivirile incerte cu `match_needs_review=True`).
4. `drift_detector` validează plauzibilitatea citirii (`D-002`: scădere `<=70%`, creștere `<=200%`, preț `>=50 RON`, similaritate titlu `>=60%`).
5. Datele valide sunt salvate în baza de date (`SiteConfig.adapter_status='healthy'`) și afișate în `DS-03` (excluzând citirile `suspect` și `error` din statistici/grafice); citirile suspecte marchează adaptorul `suspect` în `SiteConfig`/`AdapterRunLog`, salvează snapshot HTML în `storage/snapshots/` și suprimă alertele către utilizatori.

## State and storage
| What | Where | Owner | Notes |
|---|---|---|---|
| Source code & docs | Git repository | Autor / Student | Tracked across `main` / feature branches |
| Local/Test DB | data/pricemonitor.db | SQLite | Dezvoltare locală și teste `pytest` |
| Container/Prod DB | postgres_data volume | PostgreSQL 16 | Configurat prin `DATABASE_URL=postgresql+psycopg://...` |
| Error/Drift Snapshots | storage/snapshots/ | File system local | Fișiere HTML pentru depanare adaptoare |

## Configuration
| Name | Where set | Used by | Notes |
|---|---|---|---|
| DATABASE_URL | .env / docker-compose.yml | app/db/session.py | SQLite local sau PostgreSQL 16 (`postgresql+psycopg://...`) |
| SECRET_KEY | .env / config | app/core/security.py | Semnare HMAC-SHA256 cookie-uri sesiune (obligatoriu în producție) |
| ENABLE_BACKGROUND_WORKER | .env / config | app/main.py | Implicit `False` (dezactivat în teste; activabil pentru polling automat) |
| TELEGRAM_BOT_TOKEN | .env / config | Notificări Telegram | Token bot Telegram (Step 5) |
| SMTP_* | .env / config | Serviciu Email | Configurare server email pentru alerte (Step 5) |

## Build, deploy, runtime
- Python 3.12 (Docker) / 3.10+ (local)
- Gestiune dependențe prin `requirements.txt`
- Container local: `docker compose up --build` (PostgreSQL 16 + FastAPI pe port 8000, `${PORT:-8000}` în `Dockerfile`)
- Rulare worker manual: `python -m app.worker.runner --once`
- Rulare teste: `pytest -v`
- Verificare integritate ledger: `python3 docs/agents/tools/ledger-lint.py`

## Boundaries
Local repository development and academic assignment grading boundaries.
