# AI_LOG — Jurnalul Activităților Asistate de AI (Lab 1)

Jurnal cronologic al sesiunilor de lucru asistate de AI pentru proiectul **P23 · Monitor de prețuri cu scraping etic**, desfășurate în cadrul activităților de laborator ULBS (Ingineria Programării / Tehnologii Web).

---

## Sesiunea 1: Definire Scope, Interviu de Domeniu și Analiză Etică

- **Data:** 16.11.2026 – 19.11.2026
- **Obiectiv:** Identificarea nevoii reale din piață, analiza etică și tehnică a magazinelor online din România, stabilirea domeniului de aplicare (Scope) și formalizarea primelor decizii de arhitectură în ledger.

### Ce s-a cerut (Prompt / Input)
- Definirea temei de proiect pentru tema P23 (Categoria E · Integrări & fișiere).
- Conceperea și centralizarea unui sondaj de opinie structurat privind comportamentul de cumpărare online și urmărire a prețurilor (cu minim 5 respondenți reali).
- Verificarea riguroasă a legalității, a Termenilor și Condițiilor și a fișierelor `robots.txt` pentru cel puțin 5 magazine online din România, cu selectarea a 3 magazine compatibile pentru monitorizarea aceluiași tip de produs și respingerea motivată a celor incompatibile.
- Documentarea specificației complete a proiectului, a vocabularului de domeniu, soluționarea întrebării deschise privind stiva tehnologică și înregistrarea deciziilor de arhitectură aprobate.

### Ce a produs agentul (Output)
1. [INTERVIEW.md](file:///home/manol/Work/ULBS_laborator/INTERVIEW.md):
   - Centralizarea răspunsurilor de la 7 participanți reali.
   - Validarea categoriei dominante: încălțăminte și articole sportive / streetwear (71,4% voturi).
   - Frecvența optimă de verificare dedusă din nevoile utilizatorilor: interval de 6 ore (acoperă 85,8% dintre scenariile zilnice fără a bombarda serverele).
   - Reguli de alertare solicitate: prag fix de preț (57,1%), reducere procentuală $\ge 15-20\%$ (57,1%), revenire în stoc (28,6%).
   - Canale de notificare: 100% preferință pentru Email, cu Telegram ca opțiune complementară.
   - Importanța istoricului grafic al prețurilor pe săptămâni/luni: 85,7% (nota 4 și 5 din 5).
2. [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md):
   - Definirea politicii de politețe (*Politeness Policy*): pauză minimă $\ge 10\text{ secunde}$ între cereri pe același domeniu, cel mult 30 cereri/oră, identificare prin User-Agent transparent (`ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)`), verificare programatică a regulilor `robots.txt` cu cache local la 24h și minimizarea datelor colectate (exclusiv date comerciale publice, fără date cu caracter personal).
   - Analiza detaliată a celor 3 magazine acceptate: **JD Sports România** (`jdsports.ro`), **Sizeer România** (`sizeer.ro`), **Buzz Sneakers România** (`buzzsneakers.ro`) — toate permit accesul pe paginile individuale de produs, au coduri SKU corelabile și nu conțin clauze abuzive în ToS.
   - Analiza și respingerea argumentată a 3 site-uri: **Zara** (interdicție explicită de scraping în ToS, protecție WAF, brand unic), **Fashion Days** (redirecționare invalidă pe `robots.txt`), **epantofi.ro** (`robots.txt` returnează 404, protecții anti-bot).
3. [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md):
   - Definirea completă a cerințelor funcționale, rolurilor (Utilizator vs. Administrator), fluxului de date, ecranelor UI și non-obiectivelor (*out of scope*).
   - Stabilirea pragurilor precise de detecție a derivei (*drift detection*): scădere $>70\%$, creștere $>200\%$, preț invalid $\le 0\text{ RON}$ sau $<50\text{ RON}$, similaritate titlu $<60\%$, câmpuri lipsă.
4. [CONTEXT.md](file:///home/manol/Work/ULBS_laborator/CONTEXT.md):
   - Formalizarea termenilor de domeniu: *SKU*, *Canonical Product*, *Product Listing*, *Polite Polling*, *Circuit Breaker*, *Drift Detection*, *Watchlist*, *Snapshot*.
5. [README.md](file:///home/manol/Work/ULBS_laborator/README.md) & [docs/agents/ARCHITECTURE.md](file:///home/manol/Work/ULBS_laborator/docs/agents/ARCHITECTURE.md):
   - Prezentarea generală a proiectului, structura directoarelor și schema fluxului de date.
6. Registrul Ledger:
   - [docs/agents/OPEN-QUESTIONS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/OPEN-QUESTIONS.md): Răspuns și închidere pentru Q-001 (alegerea stivei).
   - [docs/agents/DECISIONS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/DECISIONS.md):
     - `D-001`: Stiva tehnologică aprobată (Python 3, FastAPI, Jinja2, Tailwind CSS, Chart.js, httpx, BeautifulSoup4, SQLite, pytest).
     - `D-002`: Politica de scraping etic și pragurile de detecție a derivei.
     - `D-003`: Persistența locală pe disc (SQLite `data/pricemonitor.db`), snapshot-uri HTML în `storage/snapshots/` și autentificare cu conturi de seed (`admin@pricemonitor.local`, `user@pricemonitor.local`).

### Ce a verificat și aprobat utilizatorul
- A validat rezultatele interviului și concluzia că produsele de tip *sneakers* reprezintă categoria ideală pentru comparație între mai mulți retaileri.
- A aprobat selectarea celor 3 magazine partenere (`jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro`) și motivele de respingere a site-urilor Zara, Fashion Days și epantofi.ro.
- A aprobat politica de politețe (10s delay, 30 req/h, 6h polling) și pragurile matematice de detecție a derivei.
- A confirmat deciziile de arhitectură `D-001`, `D-002`, `D-003` și răspunsul la `Q-001`.

---

## Sesiunea 2: Sistem de Design, Registru de Ecrane și Machete UI Interactive

- **Data:** 19.11.2026
- **Obiectiv:** Crearea direcției estetice, definirea token-urilor de design system pentru modul luminos/întunecat, inventarierea ecranelor aplicației și dezvoltarea/rafinarea iterativă a primei machete HTML responsive.

### Ce s-a cerut (Prompt / Input)
- Realizarea unui mini-interviu de stil pentru definirea direcției vizuale a monitorului de prețuri P23.
- Formalizarea specificației de design system cu token-uri CSS clare pentru culori, tipografie, spațiere și badge-uri de magazin.
- Crearea unui registru de ecrane (`docs/design/registry.yaml`) pentru toate fluxurile funcționale (DS-01 până la DS-05).
- Crearea și rafinarea iterativă a unei machete HTML interactive de înaltă fidelitate pentru ecranul principal de Watchlist (`docs/design/mocks/ds-02-watchlist.html`), eliminând orice imagine generică sau stil nespecific prin ilustrații vectoriale SVG dedicate pentru sneakers și branding P23.

### Ce a produs agentul (Output)
1. [docs/design/DESIGN.md](file:///home/manol/Work/ULBS_laborator/docs/design/DESIGN.md):
   - Direcție estetică *P23 Live Market Aesthetic*: interfață curată, funcțională, de densitate informațională ridicată, cu geometrie clară (border-radius restricționat la 2px–6px) și borduri fine de 1px fără umbre difuze.
   - Paletă cromatică duală (Light Canvas `#FFFFFF` / Dark Canvas `#0D0D0D`, Carduri `#161616`).
   - Accente de tranzacționare: Verde Forestier `#006340` / Smarald `#00A86B` pentru „Cel mai mic preț”, discounturi și stoc; Roșu Bursier `#D92D20` / `#F04438` pentru creșteri de preț și alerte de circuit breaker.
   - Tipografie tehnică specializată: `Inter` pentru etichete și titluri cu tracking strâns (`-0.025em`), `JetBrains Mono` cu cifre tabulare (`tnum`) pentru prețuri, SKU-uri și timpi.
   - Token-uri specifice per retailer: JD Sports (albastru închis/alb), Sizeer (antracit/galben vibrant), Buzz Sneakers (roșu burgund/alb).
2. [docs/design/registry.yaml](file:///home/manol/Work/ULBS_laborator/docs/design/registry.yaml):
   - Inventarierea completă a ecranelor:
     - `DS-01`: Autentificare Login & Register (`/login`).
     - `DS-02`: Dashboard Watchlist Utilizator (`/dashboard`).
     - `DS-03`: Detaliu Produs & Grafic Comparativ Chart.js (`/products/{sku}`).
     - `DS-04`: Setări Profil & Notificări Telegram/Email (`/settings`).
     - `DS-05`: Panou de Administrare Sănătate Scraper & Drift Debug (`/admin`).
3. [docs/design/mocks/ds-02-watchlist.html](file:///home/manol/Work/ULBS_laborator/docs/design/mocks/ds-02-watchlist.html):
   - Machetă HTML5/Tailwind responsive de sine stătătoare pentru ecranul principal de Watchlist.
   - Implementarea banner-ului de status al scraper-ului, a strip-ului de metrici cheie (produse urmărite, cel mai mic preț mediu, reduceri active), a controalelor de căutare/filtrare și a modalului de adăugare URL.
   - **Rafinare iterativă:** Înlocuirea placeholder-elor generice cu ilustrații SVG vectoriale de pantofi sport (profiluri detaliate de sneakers cu talpă, cusături și accente colorate pentru Nike Air Max 90, Adidas Samba OG și New Balance 550) și integrarea logoului geometric P23.

### Ce a verificat și aprobat utilizatorul
- A inspectat token-urile de design din `docs/design/DESIGN.md` și a confirmat estetica de bursă/piață sportivă.
- A verificat lista de componente și ecrane din `docs/design/registry.yaml`.
- A deschis în browser macheta `ds-02-watchlist.html`, a validat aspectul vizual profesional al ilustrațiilor SVG de sneakers, layout-ul responsive și stările de interacțiune, aprobând statusul ecranului `DS-02` ca fiind aprobat (`status: approved`).

---

## Sesiunea 3: Faza de Planificare — Pasul 1 Fundația Bazei de Date (SQLite & SQLAlchemy 2.0)

- **Data:** 19.11.2026
- **Obiectiv:** Verificarea alinierii de ansamblu înainte de codare, elaborarea planului riguros pentru Pasul 1 (Schema bazei de date SQLite/SQLAlchemy 2.0, configurare inițială și date de seed) și aprobarea formală a planului conform procedurii `/plan`.

### Ce s-a cerut (Prompt / Input)
- Verificare preliminară dacă au rămas întrebări deschise sau decizii nesoluționate.
- Urmărirea procedurii din `.claude/skills/plan/SKILL.md` pentru a concepe planul tehnic detaliat pentru **Step 1 Foundation**:
  - Schema de baze de date relațională cu SQLAlchemy 2.0 pe SQLite (`data/pricemonitor.db`).
  - Toate cele 8 entități: `User` (cu conturile predefinite `admin@pricemonitor.local` și `user@pricemonitor.local`), `CanonicalProduct`, `ProductListing`, `PriceHistory`, `WatchlistItem`, `AdapterRunLog`, `SiteConfig` (pentru jdsports, sizeer, buzzsneakers) și `NotificationLog`.
  - Mecanism de activare automată a constrângerilor de chei externe în SQLite (`PRAGMA foreign_keys=ON`).
  - Modul de securitate și hash-uire bcrypt a parolelor (`app/core/security.py`).
  - Script idempotent de seed (`app/db/seed.py`).
  - Suită de teste automate `pytest`.
- Restricție imperativă: Nu se modifică fișiere de cod ale aplicației; agentul se oprește după prezentarea planului și a tabelului de cunoștințe utilizate (*Knowledge used*) pentru obținerea aprobării.

### Ce a produs agentul (Output)
1. **Planul tehnic complet pentru Step 1 Foundation:**
   - **Size:** M (8 modele SQLAlchemy 2.0, engine SQLite cu event listener de foreign keys, securitate bcrypt, seed idempotent, structură de directoare și teste pytest).
   - **Approach:** Utilizarea claselor declarative tipizate (`DeclarativeBase`, `Mapped`, `mapped_column`), constrângeri unice și de cheie externă cu ștergere în cascadă (`ondelete="CASCADE"`), hash-uire securizată cu bcrypt și seed determinist.
   - **Tabel fișiere:** Lista exactă a celor 24 de fișiere ce urmează a fi create în faza de build (`requirements.txt`, `pytest.ini`, `.gitignore`, module `app/core/`, modele `app/db/models/`, seed `app/db/seed.py`, directoare `data/` și `storage/snapshots/`, teste `tests/`).
   - **Tabel teste automate:** 13 teste unitare și de integrare acoperind crearea tabelelor, constrângerile unice, cascadele de ștergere, securitatea parolelor și rularea idempotentă a seed-ului.
   - **Secvențiere & Riscuri:** Un singur builder, analiză a riscurilor legate de suportul de foreign keys în SQLite și precizia valorilor monetare.
   - **Tabelul Knowledge Used:**
     - `D-001`: Stiva tehnologică aprobată (confirm).
     - `D-002`: Politica de politețe și scraping etic (confirm).
     - `D-003`: Persistența SQLite, snapshot-uri și modelul de autentificare (confirm).
     - `Q-001`: Soluționarea stivei și a uneltelor (confirm).
     - `PATTERN-001 (candidate)`: Constrângeri de chei externe în SQLite și modele declarative SQLAlchemy 2.0 (confirm).
     - `PATTERN-002 (candidate)`: Idempotent Database Seeding (confirm).
2. **Actualizarea Ledger-ului:**
   - Adăugarea modelelor `PATTERN-001` și `PATTERN-002` în [docs/agents/PATTERNS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/PATTERNS.md) cu starea `candidate` și marcajul de confirmare de la utilizator (`Confirmed: 2026-11-19`).
   - Reconstruirea automată a indexului cu `python3 docs/agents/tools/ledger-lint.py --fix`.

### Ce a verificat și aprobat utilizatorul
- Utilizatorul a analizat planul detaliat și a confirmat explicit toate verdicturile din tabelul de cunoștințe utilizate:
  - `D-001`: confirm
  - `D-002`: confirm
  - `D-003`: confirm
  - `Q-001`: confirm
  - `PATTERN-001 (candidate)`: confirm
  - `PATTERN-002 (candidate)`: confirm
- A aprobat formal planul pentru Step 1 Foundation (schema bazei de date SQLite/SQLAlchemy 2.0, configurarea inițială și datele de seed).
- A decis oprirea lucrului la stadiul de plan aprobat pentru evaluarea etapei Lab 1, amânând faza de build/scriere de cod efectivă pentru laboratorul următor.

---

## Rezumatul Livrabilelor Aprobate la Finalul Etapelor de Laborator 1

| Livrabil | Cale / Fișier | Stare |
|---|---|---|
| Rezultatele Interviului Utilizatori | [INTERVIEW.md](file:///home/manol/Work/ULBS_laborator/INTERVIEW.md) | Finalizat & Aprobat |
| Analiza de Legalitate, ToS & `robots.txt` | [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md) | Finalizat & Aprobat |
| Domeniul de Aplicare & Specificație Detaliată | [docs/scope.md](file:///home/manol/Work/ULBS_laborator/docs/scope.md) | Finalizat & Aprobat |
| Vocabularul de Domeniu | [CONTEXT.md](file:///home/manol/Work/ULBS_laborator/CONTEXT.md) | Finalizat & Aprobat |
| Decizii Tehnice & Arhitecturale | [docs/agents/DECISIONS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/DECISIONS.md) (`D-001`, `D-002`, `D-003`) | Aprobate & Confirmate |
| Șabloane Tehnice de Lucru | [docs/agents/PATTERNS.md](file:///home/manol/Work/ULBS_laborator/docs/agents/PATTERNS.md) (`PATTERN-001`, `PATTERN-002`) | Înregistrate (candidate confirmed) |
| Specificație Design Tokens & Estetică | [docs/design/DESIGN.md](file:///home/manol/Work/ULBS_laborator/docs/design/DESIGN.md) | Finalizat & Aprobat |
| Registru Ecrane (DS-01 .. DS-05) | [docs/design/registry.yaml](file:///home/manol/Work/ULBS_laborator/docs/design/registry.yaml) | Finalizat & Aprobat |
| Machetă HTML/CSS Interactivă DS-02 | [docs/design/mocks/ds-02-watchlist.html](file:///home/manol/Work/ULBS_laborator/docs/design/mocks/ds-02-watchlist.html) | Finalizat & Aprobat |
| Plan Pasul 1 Fundație DB | Plan aprobat conform procedurii `/plan` | Aprobat (gata de `/build` în Lab 2) |
