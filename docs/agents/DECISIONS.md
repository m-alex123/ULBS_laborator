# Decisions — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> Constraints the code must obey. Status: `approved` (obey) · `proposed` (do not
> build on it) · `superseded-by <ID>` (kept to explain old code).
> Adding or changing an entry needs the user's OK (AGENTS.md → The gate).
<!-- graffino-agentic:end -->

## Index
- D-001 · Stiva tehnologică pentru proiectul P23
- D-002 · Politica de scraping etic și pragurile de detecție a derivei (drift detection)
- D-003 · Stocarea locală a datelor, snapshot-urile HTML și modelul de autentificare
- D-004 · Contracte HTTP și Arhitectură Web SSR (Step 2)
- D-005 · Motorul de scraping etic, adaptoarele de retail, detecția derivei și deduplicarea SKU (Step 3)
- D-006 · Mod Vizitator read-only (Guest), comparație DS-03, ingestie URL watchlist și worker de scraping (Step 4)

---

## D-001 · Stiva tehnologică pentru proiectul P23
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Aplicația se dezvoltă în Python 3 utilizând FastAPI (cu șabloane Jinja2, CSS bazat pe token-urile `docs/design/DESIGN.md` / Tailwind și Chart.js), httpx și BeautifulSoup4 pentru scraping etic (cu `urllib.robotparser`), SQLite (`data/pricemonitor.db`) pentru dezvoltare locală și teste `pytest`, respectiv PostgreSQL 16 (`psycopg`) în mediul Docker Compose / producție via `DATABASE_URL`, și pytest pentru teste automate.
- **Why:** Oferă simplitate, portabilitate maximă la dezvoltare/testare fără dependențe grele și persistență robustă cu PostgreSQL 16 în rularea containerizată și producție.
- **Evidence:** Confirmat inițial la 19.11.2026 ([docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md)) și actualizat la 25.11.2026 pentru suportul dual SQLite + PostgreSQL 16 ([docker-compose.yml](file:///home/manol/Work/ULBS_laborator/docker-compose.yml), [app/db/session.py](file:///home/manol/Work/ULBS_laborator/app/db/session.py)).

## D-002 · Politica de scraping etic și pragurile de detecție a derivei (drift detection)
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Colectarea datelor de preț și stoc respectă o politică etică strictă de politețe: verificare automată la interval implicit de 6 ore (configurabil per site), pauză minimă de 10 secunde (`delay >= 10s`) între cereri consecutive către același domeniu, cel mult 30 cereri/oră per domeniu, identificare prin User-Agent transparent (`ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)`) și verificarea programatică a regulilor `robots.txt` (cu cache reîmprospătat la 24 de ore). Pentru detecția derivei (drift detection), un adaptor este marcat automat ca suspect și notificările către utilizatori sunt suspendate dacă o citire declanșează: scădere de preț >70% într-un ciclu, creștere de preț >200% (>= 3x), preț sub 50 RON (sau <= 0 RON), similaritate a titlului sub 60% sau absența oricărui câmp obligatoriu (titlu, preț, monedă, stoc).
- **Why:** Protejează magazinele partenere de supraîncărcare și previne blocarea adresei IP, iar pragurile de derivă garantează calitatea datelor și previn alertele eronate transmise utilizatorilor la modificări structurale ale magazinelor sursă.
- **Evidence:** Confirmat și aprobat conform [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md) (secțiunile 2.2 și 2.3) și [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md) (secțiunea 1); reconfirmat la 2026-11-25 pentru Step 3.

## D-003 · Stocarea locală a datelor, snapshot-urile HTML și modelul de autentificare
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Datele aplicației sunt persistate prin SQLAlchemy 2.0 în SQLite (`data/pricemonitor.db`) local/în teste și în PostgreSQL 16 (`DATABASE_URL=postgresql+psycopg://...`) în Docker/producție, iar snapshot-urile HTML descărcate în caz de eșec sau citiri suspecte de derivă sunt salvate pe disc în directorul `storage/snapshots/` (ignorat în Git, reținând în baza de date doar calea relativă). Autentificarea utilizatorilor verifică email-ul și parola hash-uită cu `bcrypt` și emite cookie-uri `HttpOnly` (`SameSite=Lax`) semnate HMAC-SHA256 cu aplicarea rolurilor (`user` și `admin`) pe server, iar scriptul de seed populează idempotent două conturi demonstrative (`admin@pricemonitor.local` și `user@pricemonitor.local`) cu produse și istoric de prețuri preîncărcate.
- **Why:** Păstrează portabilitatea SQLite pentru testare și dezvoltare rapidă, oferă fiabilitate PostgreSQL 16 în container/producție și elimină expunerea token-urilor de sesiune în JavaScript prin cookie-uri semnate `HttpOnly`.
- **Evidence:** Confirmat la 19.11.2026 ([docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md)) și actualizat la 25.11.2026 ([app/core/security.py](file:///home/manol/Work/ULBS_laborator/app/core/security.py), [app/web/deps.py](file:///home/manol/Work/ULBS_laborator/app/web/deps.py), [app/web/routers/auth.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/auth.py)).

## D-004 · Contracte HTTP și Arhitectură Web SSR (Step 2)
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Aplicația web FastAPI (`app/main.py`) expune rute server-side Jinja2 (`DS-01` `/login`, `DS-02` `/` și `/watchlist`), endpoint-ul de monitorizare `GET /health` și verificarea de rol `GET /admin/status`, aplicând controlul accesului pe roluri (`user` / `admin`) pe server prin cookie-uri semnate `HttpOnly`; stilizarea utilizează CSS pur (`app/web/static/css/p23.css`) derivat direct din token-urile `docs/design/DESIGN.md` fără pipeline Node de build.
- **Why:** Asigură o limită clară de contract pentru Checkpoint Step 2 și menține containerul Docker Python minimal și rapid la pornire (`python -m app.db.seed && uvicorn ... --port ${PORT:-8000}`).
- **Evidence:** Aprobat de utilizator la 25.11.2026 și implementat în [app/main.py](file:///home/manol/Work/ULBS_laborator/app/main.py), [API.md](file:///home/manol/Work/ULBS_laborator/API.md) și [docs/agents/CONTRACTS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/CONTRACTS.md).

## D-005 · Motorul de scraping etic, adaptoarele de retail, detecția derivei și deduplicarea SKU (Step 3)
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Motorul de scraping trăiește în `app/scraping/` și separă parsarea pură a prețurilor/stocului (`price_parser.py`), clientul HTTP sincron politicos (`polite_client.py` cu `urllib.robotparser` + reguli wildcard RFC-9309 `*`/`$`, cache 24h fail-closed, pauză `>=10s` și plafon `<=30 req/h`), adaptoarele declarative de magazin (`adapters/` pentru `jdsports`, `sizeer`, `buzzsneakers` testate offline pe `tests/fixtures/`), detecția derivei (`drift_detector.py`) care marchează `SiteConfig.adapter_status = 'suspect'` și `AdapterRunLog(status='suspect')`, salvează snapshot HTML în `storage/snapshots/`, păstrează ultimul preț valid și suprimă alertele către utilizatori, precum și deduplicarea cross-site (`deduplicator.py`) care normalizează codurile SKU și marchează potrivirile incerte pe `ProductListing` (`match_needs_review`, `match_confidence`, `suggested_canonical_product_id`) pentru confirmare de administrator.
- **Why:** Garantează testabilitatea 100% offline a adaptoarelor și politicii etice, previne alertele false la modificări de layout ale magazinelor sursă și pregătește date curate pentru panoul de administrare (Step 4) fără a încălca constrângerea unică `(canonical_product_id, store)`.
- **Evidence:** Aprobat de utilizator la 2026-11-25; implementat în `app/scraping/`, [site_config.py](file:///home/manol/Work/ULBS_laborator/app/db/models/site_config.py), [product_listing.py](file:///home/manol/Work/ULBS_laborator/app/db/models/product_listing.py) și verificat în `tests/test_price_parser.py`, `tests/test_polite_client.py`, `tests/test_adapters.py`, `tests/test_drift_detector.py` și `tests/test_deduplicator.py`.

## D-006 · Mod Vizitator read-only (Guest), comparație DS-03, ingestie URL watchlist și worker de scraping (Step 4)
- **Status:** approved
- **Confirmed:** 2026-11-25
- **Rule:** Vizitatorii neautentificați (Guest) pot naviga catalogul public read-only (`GET /catalog`) și pagina detaliată `DS-03` (`GET /products/{canonical_id}`) fără autentificare (inclusiv prin opțiunea „Continuă ca Vizitator (Guest)” din `/login` și indicatorul Guest cu link-uri `Autentificare`/`Înregistrare` din header), păstrând rutele personale și de administrare (`/`, `/watchlist`, `POST /watchlist`, `POST /watchlist/{canonical_id}/target`, `POST /watchlist/{canonical_id}/delete`, `/admin/status`) protejate conform `C-002` și `C-003`. Înregistrarea publică (`GET/POST /register`) creează exclusiv conturi `role="user"` cu parolă de minim 12 caractere hash-uită `bcrypt`. Pagina `DS-03` exclude explicit citirile `PriceHistory` cu `status IN ('suspect', 'error')` din statisticile de minim/maxim/medie și din istoricul afișat. Worker-ul `app/worker/runner.py` rulează prin CLI (`python -m app.worker.runner --once`) și buclă opțională dezactivată implicit (`ENABLE_BACKGROUND_WORKER=False`).
- **Why:** Permite evaluarea și navigarea imediată a comparațiilor cross-site fără cont, protejează integritatea datelor personale/admin, elimină alertele false din istoricul `DS-03` și previne pornirea accidentală a scraping-ului în timpul testelor `pytest`.
- **Evidence:** Aprobat de utilizator la 2026-11-25; implementat în [catalog.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/catalog.py), [auth.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/auth.py), [watchlist.py](file:///home/manol/Work/ULBS_laborator/app/web/routers/watchlist.py), [ingestion_service.py](file:///home/manol/Work/ULBS_laborator/app/services/ingestion_service.py), [runner.py](file:///home/manol/Work/ULBS_laborator/app/worker/runner.py) și verificat în `tests/test_guest_and_product_detail.py`, `tests/test_watchlist_ingestion.py` și `tests/test_worker_runner.py`.
