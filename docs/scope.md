# SCOPE — P23: Monitor de prețuri cu scraping etic

- **Proiect:** P23 · Monitor de prețuri cu scraping etic (Categoria E · Integrări & fișiere)
- **Autor / Student:** ULBS Coursework
- **Data validării specificației:** 19.11.2026
- **Surse de fundamentare:** [docs/brief.md](file:///home/manol/Work/ULBS_laborator/docs/brief.md), [INTERVIEW.md](file:///home/manol/Work/ULBS_laborator/INTERVIEW.md), [ETHICS.md](file:///home/manol/Work/ULBS_laborator/ETHICS.md)

---

## 1. Rezumat și Obiectiv

Aplicația este un sistem complet de urmărire automată și etică a prețurilor și disponibilității pentru produse din categoria **încălțăminte și articole sportive (sneakers)** de pe **3 retaileri din România**. Sistemul oferă deduplicare automată pe bază de SKU/model, istoric de prețuri cu grafice interactive, alertare pe Email și Telegram, detectare proactivă a derivei adaptoarelor (*drift detection*) și un panou dedicat de administrare a sănătății scraper-ului.

---

## 2. Variabilele Proiectului (Validate)

### 2.1. Categoria și cele 3 site-uri țintă
- **Categorie:** Încălțăminte și articole sportive (*sneakers* / streetwear).
- **Magazine aprobate:**
  1. **JD Sports România** (`https://www.jdsports.ro`)
  2. **Sizeer România** (`https://sizeer.ro`)
  3. **Buzz Sneakers România** (`https://www.buzzsneakers.ro`)
- *Magazine analizate și respinse conform politicii etice:* Zara (`zara.com` - interdicție ToS/WAF), Fashion Days (`fashiondays.ro` - robots.txt invalid), epantofi.ro (`epantofi.ro` - 404 robots.txt / protecții anti-bot).

### 2.2. Intervalul de verificare (Polling) și Politica de Politețe
- **Interval implicit de verificare:** **6 ore** (de 4 ori pe zi) pentru toate cele 3 site-uri.
- **Configurabilitate:** Administratorul poate ajusta intervalul individual per site/adaptor din interfață.
- **Pauză minimă între cereri către același domeniu:** $\ge 10\text{ secunde}$.
- **Limită maximă de cereri per domeniu:** $\le 30\text{ cereri/oră}$.
- **Identificare User-Agent:** `ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)`.
- **Verificare `robots.txt`:** Validare programatică în cod înainte de fiecare accesare, cu cache local reîmprospătat la 24 de ore.

### 2.3. Pragurile de plauzibilitate pentru detecția derivei (Drift Detection)
Un adaptor este marcat automat ca **suspect** (cu alertă către administrator și suspendarea notificărilor către utilizatori) dacă o citire declanșează oricare dintre următoarele condiții:
1. **Scădere extremă de preț:** Scădere $> 70\%$ față de ultima citire validă într-un singur ciclu.
2. **Creștere extremă de preț:** Creștere $> 200\%$ (de $\ge 3$ ori prețul anterior).
3. **Preț minim / invalid:** Preț $\le 0\text{ RON}$ sau preț $< 50\text{ RON}$ (previne parsarea greșită a taxelor de transport sau a valorilor nule).
4. **Similaritate titlu:** Scorul de similaritate al titlului extras față de titlul anterior scade sub $60\%$ (indică selector modificat sau pagină de redirect/eroare).
5. **Câmpuri obligatorii lipsă:** Absența prețului, a titlului, a monedei sau a statusului de stoc.

---

## 3. Roluri și Permisiuni

### 3.1. Utilizator Obișnuit
- Înregistrare și autentificare în aplicație (email și parolă).
- Administrare proprie a listei de urmărire (*Watchlist*):
  - Adăugare URL-uri de produs din cele 3 magazine suportate.
  - Setare reguli de alertare: prag fix de preț (RON), reducere procentuală minimă ($\ge 15-20\%$) și/sau revenire în stoc.
  - Configurare canale de notificare (Email activat implicit, Telegram opțional).
- Vizualizare comparativă a aceluiași produs pe cele 3 magazine (identificat prin SKU) cu marcarea ofertei „Cel mai bun preț acum”.
- Vizualizare istoric și grafic de evoluție a prețului.

### 3.2. Administrator
- Deține toate drepturile utilizatorului obișnuit.
- Acces la **Panoul de Administrare (Admin Health Dashboard)**:
  - Monitorizare stare adaptoare (`Healthy`, `Suspect`, `Degraded`, `Circuit Open`).
  - Rate de succes, timestamp-ul ultimei rulări, loguri de eroare.
  - Inspectarea alertelor de derivă și vizualizarea/descărcarea snapshot-urilor HTML salvate la eroare/derivă.
  - Validare sau respingere manuală a unei citiri marcate ca suspecte.
  - Ajustare intervale de polling și limite de rate-limiting per domeniu.
  - Declanșare manuală a unei verificări (*manual rescan*).

### 3.3. Autentificare și Conturi Preconfigurate (Seed)
- Autentificare pe bază de sesiune securizată / JWT cu parole hash-uite.
- Script de seed la inițializarea bazei de date cu două conturi:
  - Admin: `admin@pricemonitor.local`
  - Utilizator Demo: `user@pricemonitor.local` (cu produse și istoric de preț preîncărcate).

---

## 4. Arhitectura Tehnică, Modelul de Date și Stocarea

### 4.1. Stiva Tehnologică (Confirmată)
- **Limbaj și Runtime:** Python 3.
- **Backend & Web UI:** FastAPI cu randare server-side prin template-uri Jinja2, stilizare responsive modernă prin Tailwind CSS și grafice interactive prin Chart.js.
- **Scraping etic & parsare:** `httpx` (pentru cereri HTTP asincrone/sincrone) și `BeautifulSoup4` (pentru extragerea datelor din HTML).
- **Verificare `robots.txt`:** Modulul standard din biblioteca Python `urllib.robotparser` (cu mecanism de cache local la 24h).
- **Bază de date:** SQLite (`data/pricemonitor.db`), cu rulare locală, migrări automate și script de seed.
- **Suită de testare:** `pytest` (cu teste pentru parsarea prețurilor, calculul similarității titlurilor și regulile robots.txt pe fixtures HTML salvate).

### 4.2. Entități Principale
1. **User:** `id`, `email`, `password_hash`, `role` (`user`, `admin`), `telegram_chat_id`, `created_at`.
2. **CanonicalProduct:** `id`, `name`, `brand`, `sku` (cod model/producător pentru deduplicare între site-uri), `image_url`, `created_at`.
3. **ProductListing:** `id`, `canonical_product_id`, `store` (`jdsports`, `sizeer`, `buzzsneakers`), `url`, `current_price`, `original_price` (preț tăiat), `raw_title`, `currency`, `in_stock`, `last_checked_at`, `is_active`.
4. **PriceHistory:** `id`, `product_listing_id`, `price`, `currency`, `in_stock`, `recorded_at`, `status` (`valid`, `suspect`, `error`).
5. **WatchlistItem / AlertRule:** `id`, `user_id`, `canonical_product_id`, `target_price`, `min_discount_percent`, `notify_stock`, `notify_email`, `notify_telegram`, `created_at`.
6. **AdapterRunLog:** `id`, `store`, `status` (`success`, `failed`, `suspect`), `error_message`, `snapshot_path`, `duration_ms`, `created_at`.
7. **SiteConfig:** `id`, `store`, `polling_interval_minutes` (implicit 360), `min_delay_seconds` (implicit 10), `max_requests_per_hour` (implicit 30), `circuit_breaker_open` (boolean).
8. **NotificationLog:** `id`, `user_id`, `product_listing_id`, `channel` (`email`, `telegram`), `trigger_reason`, `message_payload`, `sent_at`.

### 4.3. Stocare Fișiere și Snapshot-uri HTML
- Fișierele HTML descărcate în caz de eșec sau citire suspectă sunt salvate pe disc în `storage/snapshots/` (cu timestamp și identificator adaptor).
- Directorul `storage/snapshots/` este ignorat în Git (`.gitignore`) și creat automat la pornirea aplicației.
- În baza de date se reține doar calea relativă (`snapshot_path`).

---

## 5. Ecrane și Interfață Grafică (UI)

Aplicație web responsive realizată cu HTML semantic, Tailwind CSS și Chart.js:
1. **Autentificare:** Pagini curate pentru *Login* și *Register*.
2. **Dashboard Utilizator / Watchlist:**
   - Lista produselor urmărite, afișând imaginea, denumirea, badge-ul „Cel mai bun preț acum”, statusul de stoc și variația procentuală.
   - Formular / Modal de adăugare URL și configurare praguri de alertă.
3. **Detaliu Produs & Comparativ:**
   - Tabel comparativ în timp real între cele 3 magazine (`jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro`).
   - Grafic interactiv Chart.js cu istoricul prețurilor pe săptămâni/luni, minim, maxim și medie istorică.
4. **Setări Profil & Notificări:**
   - Preferințe de alertare (activare Email, instrucțiuni de legare Telegram bot și setare Chat ID).
   - Log vizibil al alertelor trimise recent către utilizator.
5. **Panou de Administrare (Admin Health Dashboard):**
   - Vizualizare status per adaptor (succes, erori, circuit breaker).
   - Listă citiri suspecte (drift) cu buton de inspectare snapshot HTML și acțiuni de aprobare/respingere.
   - Formular configurare parametri site (polling, limite de politețe) și buton de *Manual Rescan*.

---

## 6. Excluderi Explicite (Out of Scope / Non-Goals)

1. **Fără achiziție automată / Auto-checkout:** Aplicația monitorizează și alertează; nu plasează comenzi automate și nu stochează date de plată/carduri.
2. **Fără ocolire anti-bot sau bypass CAPTCHA:** Nu se sparg sisteme Cloudflare/WAF și nu se folosesc rețele de proxy ilegitime; dacă un site blochează cererea, adaptorul intră în mod de protecție (circuit breaker).
3. **Fără crawling masiv pe categorii sau pagini de căutare:** Se monitorizează strict URL-urile individuale de produs adăugate de utilizatori, respectând interdicția pe `/search` din `robots.txt`.
4. **Fără aplicații mobile native:** Interfața este o aplicație web responsive (desktop & mobile), complementată de botul de Telegram.
5. **Fără plăți, abonamente sau monetizare:** Proiect strict educațional/academic.
6. **Fără alte categorii sau alte magazine:** Strict încălțăminte sport (*sneakers*) pe cele 3 domenii aprobate.
7. **Monedă unică:** Exclusiv RON (moneda comună celor 3 magazine din România).
8. **Fără colectare de recenzii sau date personale din magazine:** Nu se stochează comentarii sau date despre utilizatorii magazinelor sursă (respectare GDPR).
9. **Fără monitorizare granulară pe mărimi individuale:** Monitorizarea vizează disponibilitatea generală a produsului (În stoc / Epuizat) la nivel de pagină, fără simulare de selecție dropdown pe mărimi.

---

## 7. Întrebări Deschise Rămase (Open Questions)

- **Q-001 (Tehnologie și Stack):** *Răspuns și clarificat* la data de 19.11.2026. Stiva aprobată: Python 3, FastAPI, Jinja2, Tailwind CSS, Chart.js, httpx, BeautifulSoup4, SQLite și pytest. Nu mai există blocaje sau întrebări deschise pentru faza de planificare.
