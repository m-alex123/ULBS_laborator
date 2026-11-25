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
  │     ├── services/           (Servicii domeniu, ex. watchlist_service.py)
  │     ├── web/                (Routere health/auth/watchlist, deps, Jinja2, static CSS/JS)
  │     ├── scrapers/           (Step 3: adaptoare jdsports, sizeer, buzzsneakers)
  │     └── worker/             (Step 3-4: scheduler, circuit breaker, drift detection)
  ├── data/                     (Bază de date locală SQLite: pricemonitor.db)
  ├── storage/snapshots/        (Snapshot-uri HTML salvate la erori/derivă)
  └── tests/                    (Teste unitare și integrare pytest)
```

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| Documentation & Contracts | docs/, API.md, README.md, TODO.md | Guvernanță, specificații, decizii, contracte HTTP | Dezvoltatori, Evaluatori |
| Web Application | app/main.py, app/web/ | Rute FastAPI (`/health`, `/login`, `/watchlist`), sesiuni `HttpOnly`, șabloane Jinja2 | Utilizatori, Administrator |
| Domain Services | app/services/ | Agregare watchlist, calcul cel mai mic preț, sparkline, filtrare/sortare | Web App, Database |
| Security & Config | app/core/ | Setări mediu (`pydantic-settings`), hashing `bcrypt`, cookie-uri semnate HMAC-SHA256 | Web App, Database |
| Database & Models | app/db/, data/ | Modele SQLAlchemy 2.0, engine dual SQLite / PostgreSQL 16, seed idempotent | Web App, Services |
| Scraping Adapters (planned) | app/scrapers/ | Extragere date, politețe (delay $\ge$10s, rate limits), validare `robots.txt` | Magazine online |
| Worker & Scheduler (planned) | app/worker/ | Rulare automată la 6 ore, detecție derivă, snapshots la eroare | Bază de date, Storage |

## Data flow
1. Utilizatorul adaugă un URL de produs în aplicație și configurează praguri de alertă.
2. Worker-ul verifică programat la 6h magazinele (respectând `robots.txt`, limită de 30 req/h și delay 10s).
3. Modulul de detecție a derivei validează plauzibilitatea citirii (scădere $<70\%$, preț $>50\text{ RON}$, similaritate titlu $>60\%$).
4. Datele valide sunt salvate în SQLite și agregate pe produs canonic; citirile suspecte generează alertă pentru admin și snapshot HTML în `storage/snapshots/`.
5. Dacă prețul scade sub prag sau produsul revine în stoc, utilizatorul este alertat prin Email și/sau Telegram.

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
| TELEGRAM_BOT_TOKEN | .env / config | Notificări Telegram | Token bot Telegram (Step 5) |
| SMTP_* | .env / config | Serviciu Email | Configurare server email pentru alerte (Step 5) |

## Build, deploy, runtime
- Python 3.12 (Docker) / 3.10+ (local)
- Gestiune dependențe prin `requirements.txt`
- Container local: `docker compose up --build` (PostgreSQL 16 + FastAPI pe port 8000, `${PORT:-8000}` în `Dockerfile`)
- Rulare teste: `pytest -v`
- Verificare integritate ledger: `python3 docs/agents/tools/ledger-lint.py`

## Boundaries
Local repository development and academic assignment grading boundaries.
