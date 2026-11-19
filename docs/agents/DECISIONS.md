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

---

## D-001 · Stiva tehnologică pentru proiectul P23
- **Status:** approved
- **Confirmed:** 2026-11-19
- **Rule:** Aplicația se dezvoltă în Python 3 utilizând FastAPI (cu șabloane Jinja2, Tailwind CSS și Chart.js), httpx și BeautifulSoup4 pentru scraping etic (cu `urllib.robotparser`), SQLite (`data/pricemonitor.db`) pentru stocarea datelor și pytest pentru teste automate.
- **Why:** Oferă simplitate, portabilitate maximă, pornire rapidă fără servicii externe la evaluare și unelte native excelente pentru scraping etic și parsare HTML.
- **Evidence:** Confirmat de utilizator în data de 19.11.2026 în urma soluționării Q-001 și documentat în [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md).

## D-002 · Politica de scraping etic și pragurile de detecție a derivei (drift detection)
- **Status:** approved
- **Confirmed:** 2026-11-19
- **Rule:** Colectarea datelor de preț și stoc respectă o politică etică strictă de politețe: verificare automată la interval implicit de 6 ore (configurabil per site), pauză minimă de 10 secunde (`delay >= 10s`) între cereri consecutive către același domeniu, cel mult 30 cereri/oră per domeniu, identificare prin User-Agent transparent (`ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)`) și verificarea programatică a regulilor `robots.txt` (cu cache reîmprospătat la 24 de ore). Pentru detecția derivei (drift detection), un adaptor este marcat automat ca suspect și notificările către utilizatori sunt suspendate dacă o citire declanșează: scădere de preț >70% într-un ciclu, creștere de preț >200% (>= 3x), preț sub 50 RON (sau <= 0 RON), similaritate a titlului sub 60% sau absența oricărui câmp obligatoriu (titlu, preț, monedă, stoc).
- **Why:** Protejează magazinele partenere de supraîncărcare și previne blocarea adresei IP, iar pragurile de derivă garantează calitatea datelor și previn alertele eronate transmise utilizatorilor la modificări structurale ale magazinelor sursă.
- **Evidence:** Confirmat și aprobat conform [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md) (secțiunile 2.2 și 2.3) și [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md) (secțiunea 1).

## D-003 · Stocarea locală a datelor, snapshot-urile HTML și modelul de autentificare
- **Status:** approved
- **Confirmed:** 2026-11-19
- **Rule:** Datele aplicației sunt persistate local într-o bază de date SQLite (`data/pricemonitor.db`), iar snapshot-urile HTML descărcate în caz de eșec sau citiri suspecte de derivă sunt salvate pe disc în directorul `storage/snapshots/` (ignorat în Git, reținând în baza de date doar calea relativă). Autentificarea utilizatorilor se bazează pe email și parolă hash-uită (cu rolurile `user` și `admin`), iar scriptul de seed populează la inițializare două conturi demonstrative: administrator (`admin@pricemonitor.local`) și utilizator demo (`user@pricemonitor.local`) cu produse și istoric de prețuri preîncărcate.
- **Why:** Oferă portabilitate maximă și pornire instantanee la evaluare fără servicii externe sau containere de baze de date, separă stocarea fișierelor HTML voluminoase de baza relațională și pune la dispoziție conturi gata configurate pentru verificarea imediată a funcționalităților.
- **Evidence:** Confirmat și aprobat conform [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md) (secțiunile 3.3, 4.1, 4.2 și 4.3).
