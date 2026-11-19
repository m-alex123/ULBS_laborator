# Decisions — ULBS_laborator

<!-- graffino-agentic:begin v1 -->
> Constraints the code must obey. Status: `approved` (obey) · `proposed` (do not
> build on it) · `superseded-by <ID>` (kept to explain old code).
> Adding or changing an entry needs the user's OK (AGENTS.md → The gate).
<!-- graffino-agentic:end -->

## Index
- D-001 · Stiva tehnologică pentru proiectul P23

---

## D-001 · Stiva tehnologică pentru proiectul P23
- **Status:** approved
- **Confirmed:** 2026-11-19
- **Rule:** Aplicația se dezvoltă în Python 3 utilizând FastAPI (cu șabloane Jinja2, Tailwind CSS și Chart.js), httpx și BeautifulSoup4 pentru scraping etic (cu `urllib.robotparser`), SQLite (`data/pricemonitor.db`) pentru stocarea datelor și pytest pentru teste automate.
- **Why:** Oferă simplitate, portabilitate maximă, pornire rapidă fără servicii externe la evaluare și unelte native excelente pentru scraping etic și parsare HTML.
- **Evidence:** Confirmat de utilizator în data de 19.11.2026 în urma soluționării Q-001 și documentat în [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md).
