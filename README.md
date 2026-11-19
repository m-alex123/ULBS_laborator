# P23 · Monitor de prețuri cu scraping etic

Proiect realizat în cadrul activităților de laborator ULBS (Ingineria Programării / Tehnologii Web).

## Despre Proiect

Sistem automat de monitorizare a prețurilor și disponibilității pentru produse din categoria **încălțăminte și articole sportive (sneakers)** pe 3 magazine din România:
- **JD Sports România** (`jdsports.ro`)
- **Sizeer România** (`sizeer.ro`)
- **Buzz Sneakers România** (`buzzsneakers.ro`)

Aplicația implementează colectare etică de date (cu respectarea strictă a `robots.txt`, limitare de debit și pauze între cereri), deduplicare multi-magazin după SKU/model, istoric grafic al prețurilor, alertare pe Email & Telegram și un mecanism inovator de **detecție a derivei adaptoarelor (drift detection)** cu captură automată de snapshot-uri HTML pentru depanare.

## Documentație și Fundamentare

- [docs/brief.md](file:///home/manol/Work/ULBS_laborator/docs/brief.md) — Cerințele oficiale ale temei de laborator (P23).
- [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md) — Specificația completă și domeniul de aplicare validate.
- [INTERVIEW.md](file:///home/manol/Work/ULBS_laborator/INTERVIEW.md) — Sondaj de nevoi reale realizat cu respondenți umani (7 participanți).
- [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md) — Analiză de legalitate, ToS, `robots.txt` și politică de politețe.
- [docs/agents/ARCHITECTURE.md](file:///home/manol/Work/ULBS_laborator/docs/agents/ARCHITECTURE.md) — Arhitectura generală a aplicației și fluxul de date.
- [docs/agents/DECISIONS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/DECISIONS.md) — Registrul de decizii arhitecturale (inclusiv D-001 privind stiva tehnologică).

## Stiva Tehnologică (D-001)

- **Limbaj:** Python 3.10+
- **Backend & UI:** FastAPI, șabloane server-side Jinja2, Tailwind CSS, Chart.js
- **Scraping etic:** `httpx`, `BeautifulSoup4`, `urllib.robotparser`
- **Bază de date:** SQLite (`data/pricemonitor.db`)
- **Testare:** `pytest`

## Reguli de Guvernanță

Proiectul respectă instrucțiunile stabilite în [AGENTS.md](file:///home/manol/Work/ULBS_laborator/AGENTS.md). Integritatea ledger-ului este verificată automat cu:
```bash
python3 docs/agents/tools/ledger-lint.py
```
