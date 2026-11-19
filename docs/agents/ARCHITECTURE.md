# Architecture — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> How this repo is built, generated from the code at backfill and kept current by
> whoever changes the structure. The code wins: when this page is wrong, fix it.
<!-- graffino-agentic:end -->

## Overview
Proiectul P23: Monitor de prețuri cu scraping etic pentru încălțăminte sport (sneakers) pe 3 magazine partenere din România (`jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro`), cu respectarea `robots.txt`, deduplicare după SKU, detecție de derivă a adaptoarelor și alertare prin Email și Telegram.

```text
[Repository Root]
  ├── docs/             (Cerințe, brief, scope, decizii, întrebări, patterns)
  ├── app/              (Cod sursă aplicație: web, scraping, worker, modele, alerte)
  │     ├── scrapers/   (Adaptoare per site: jdsports, sizeer, buzzsneakers)
  │     ├── worker/     (Scheduler, coadă job-uri, circuit breaker, drift detection)
  │     └── web/        (Rute FastAPI, șabloane Jinja2, static CSS/JS)
  ├── data/             (Bază de date SQLite: pricemonitor.db)
  ├── storage/          (Snapshot-uri HTML salvate la erori/derivă)
  └── tests/            (Teste unitare și de integrare pytest pe fixtures HTML)
```

## Parts
| Part | Path | Responsibility | Talks to |
|---|---|---|---|
| Documentation | docs/, docs/agents | Guvernanță, specificații, decizii tehnice și etice | Dezvoltatori, Evaluatori |
| Web Application | app/web | Interfață grafică utilizator & panou admin (FastAPI + Jinja2 + Chart.js) | Utilizatori, Administrator |
| Scraping Adapters | app/scrapers | Extragere date, politețe (delay $\ge$10s, rate limits), validare `robots.txt` | Magazine online |
| Worker & Scheduler | app/worker | Rulare automată la 6 ore, detecție derivă, snapshots la eroare | Bază de date, Storage |
| Database & Models | app/db, data/ | Modele de date, persistență SQLite, deduplicare SKU | Web App, Worker |
| Notifications | app/services | Trimitere alerte către utilizatori/admin (Email, Telegram) | Servicii externe alerte |

## Data flow
1. Utilizatorul adaugă un URL de produs în aplicație și configurează praguri de alertă.
2. Worker-ul verifică programat la 6h magazinele (respectând `robots.txt`, limită de 30 req/h și delay 10s).
3. Modulul de detecție a derivei validează plauzibilitatea citirii (scădere $<70\%$, preț $>50\text{ RON}$, similaritate titlu $>60\%$).
4. Datele valide sunt salvate în SQLite și agregate pe produs canonic; citirile suspecte generează alertă pentru admin și snapshot HTML în `storage/snapshots/`.
5. Dacă prețul scade sub prag sau produsul revine în stoc, utilizatorul este alertat prin Email și/sau Telegram.

## State and storage
| What | Where | Owner | Notes |
|---|---|---|---|
| Source code & docs | Git repository | Autor / Student | Tracked in main branch |
| Application DB | data/pricemonitor.db | SQLite | Date utilizatori, produse, istoric prețuri, loguri |
| Error/Drift Snapshots | storage/snapshots/ | File system local | Fișiere HTML pentru depanare adaptoare |

## Configuration
| Name | Where set | Used by | Notes |
|---|---|---|---|
| DATABASE_URL | .env / config | Bază de date | Cale către fișierul SQLite |
| TELEGRAM_BOT_TOKEN | .env / config | Notificări Telegram | Token bot Telegram |
| SMTP_* | .env / config | Serviciu Email | Configurare server email pentru alerte |

## Build, deploy, runtime
- Python 3.10+
- Gestiune dependențe prin `requirements.txt`
- Rulare teste: `pytest`
- Verificare integritate ledger: `python3 docs/agents/tools/ledger-lint.py`

## Boundaries
Local repository development and academic assignment grading boundaries.
