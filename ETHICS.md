# ETHICS · Analiza de legalitate, ToS și robots.txt (P23)

- **Data analizei:** 18.11.2026
- **Categoria monitorizată:** Încălțăminte și articole sportive (sneakers)

---

## 1. Politica generală de politețe (Politeness Policy)
- **Identificare transparentă:** Toate cererile HTTP utilizează un `User-Agent` propriu și identificabil: `ULBS-Web2-PriceMonitor/1.0 (+https://github.com/m-alex123/ULBS_laborator)` (evitând agenți generici blocați în `robots.txt`, precum `wget`).
- **Verificarea `robots.txt` în cod:** Înainte de fiecare cerere HTTP către un domeniu, worker-ul verifică regulile `robots.txt` (cache-uite local și reîmprospătate la 24h) și blochează orice URL care se potrivește unei reguli `Disallow`.
- **Rate limiting și pauze între cereri:** Minim **10 secunde** pauză (`delay >= 10s`) între două cereri către același domeniu, maxim **30 cereri/oră** per domeniu, rulare programată la interval de **6 ore**.
- **Minimizarea datelor și GDPR:** Colectăm exclusiv date publice comerciale despre produse (titlu, cod SKU/producător, preț curent, preț întreg, monedă, status stoc, URL imagine, URL produs). Nu colectăm date cu caracter personal, recenzii, conturi de utilizator sau elemente protejate de drepturi de autor (descrieri lungi, bannere).

---

## 2. Site-uri acceptate (3 retaileri compatibili)

### Site 1: JD Sports România (`https://www.jdsports.ro`) — ACCEPTAT
- **Data verificării:** 18.11.2026
- **Analiză `robots.txt` (`https://www.jdsports.ro/robots.txt`):**
  - `User-agent: *` permite accesul la paginile individuale de produs (URL-uri directe la rădăcină, fără extensie, de tip `/nume-produs-cod-sku`).
  - Interzice explicit rutele de căutare (`/search`, `/aisearch*`), coșul (`/cos/*`), contul (`/login`, `/profil`, `/favorite`), filtrele combinatorii (`/*_*/*_*/*_*`), rutele interne (`/produs/`, `/product/`) și URL-urile cu punct (`/*.*`).
- **Analiză Termeni și Condiții (`https://www.jdsports.ro/regulamente`):**
  - Operat de MIG Marketing Investment Group Ro S.R.L.; documentul reglementează condițiile comerciale de vânzare, livrare, retur și prelucrarea datelor personale ale clienților. Nu conține interdicții explicite împotriva citirii automate, neintruzive, a datelor publice de preț și stoc.
- **Justificare etică și tehnică:** Accesăm strict URL-uri individuale de produs adăugate de utilizator, cu pauză de minim 10s între cereri și interval de 6 ore, fără impact asupra serverului.

### Site 2: Sizeer România (`https://sizeer.ro`) — ACCEPTAT
- **Data verificării:** 18.11.2026
- **Analiză `robots.txt` (`https://sizeer.ro/robots.txt`):**
  - `User-agent: *` permite paginile individuale de produs (URL-uri directe la rădăcină, fără `/produs/` sau `/product/`).
  - Interzice rutele de căutare (`/search*`, `/aisearch*`), coș (`/cos/*`), autentificare (`/login`, `/registration`, `/profile`), filtre multiple (`/*-*/*-*/*-*`) și rute interne (`/produs/*`, `/product/*`).
- **Analiză Termeni și Condiții (`https://sizeer.ro/regulamentul-magazinului`):**
  - Operat de MIG Marketing Investment Group Ro S.R.L.; regulamentul vizează exclusiv contractele de vânzare la distanță și protecția datelor (GDPR), fără clauze care să interzică monitorizarea personală a prețurilor publice.
- **Justificare etică și tehnică:** Folosește aceeași structură de catalog și coduri SKU ca JD Sports, permițând compararea directă a aceluiași produs cu un volum minim de cereri (1 cerere / produs / 6 ore).

### Site 3: Buzz Sneakers România (`https://www.buzzsneakers.ro`) — ACCEPTAT
- **Data verificării:** 18.11.2026
- **Analiză `robots.txt` (`https://www.buzzsneakers.ro/robots.txt`):**
  - `User-agent: *` permite accesul la paginile individuale de produs și categorii.
  - Interzice exclusiv parametrii de căutare (`/*?search=`), vizualizările iframe (`/*?iframeView=1$`), fișierele `.php` directe (`/*.php$`), parametrii de sesiune (`/*?SID=`) și URL-urile marcate cu `/*crawl=no`.
- **Analiză Termeni și Condiții (`https://www.buzzsneakers.ro/termeni-si-conditii`):**
  - Operat de Sport Vision Trading S.R.L.; protejează drepturile de proprietate intelectuală asupra designului, mărcilor și textelor comerciale (interzicând republicarea comercială a conținutului), fără a restricționa citirea privată, neintruzivă, a informațiilor publice despre prețuri și stocuri.
- **Justificare etică și tehnică:** Oferă un al treilea punct independent de comparație a prețurilor pentru aceleași modele de încălțăminte sport, cu reguli `robots.txt` clare și permisive.

---

## 3. Site-uri analizate și respinse (conform politicii etice)

### Zara (`https://www.zara.com`) — RESPINS
- **Motiv etic și tehnic:** Termenii și Condițiile interzic explicit colectarea automată de date (*data mining / scraping*), iar platforma utilizează protecții WAF agresive. În plus, comercializează exclusiv brand propriu, nepermițând compararea aceluiași produs între mai mulți retaileri.

### Fashion Days (`https://www.fashiondays.ro`) — RESPINS
- **Motiv tehnic și etic:** Cererea către `/robots.txt` redirecționează către pagina principală (HTML), iar catalogul este protejat împotriva cererilor automate.

### epantofi.ro (`https://www.epantofi.ro`) — RESPINS
- **Motiv tehnic și etic:** `/robots.txt` returnează `404 Not Found`, iar paginile de produs aplică protecții anti-bot care ar necesita ocolirea mecanismelor de securitate (contrar principiilor de scraping etic).