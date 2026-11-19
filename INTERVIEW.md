# INTERVIEW · P23 · Monitor de prețuri cu scraping etic

- **Data colectării:** 16.11.2026
- **Metodă:** Chestionar structurat (*„Obiceiuri de cumpărare și urmărire a prețurilor”* — 7 respondenți) + discuții de clarificare cu participanții (cu acordul acestora).
- **Scop:** Validarea nevoii reale, alegerea categoriei de produse, a frecvenței de verificare și a declanșatorilor pentru alerte.

---

## 1. Concluzii cheie și decizii derivate

1. **Categoria aleasă — Haine / Încălțăminte / Articole sportive:** Este cea mai votată categorie din sondaj (**5 din 7 respondenți — 71,4%**), urmată de Telefoane / Gadget-uri / Electrocasnice (42,9%).
2. **Alegerea celor 3 site-uri compatibile:** Respondenții au menționat magazine de fashion/sneakers precum **JD Sports**, **Zara**, **Zalando**, **Vinted**, **Stradivarius**. În urma analizei din `ETHICS.md` (respectarea `robots.txt`, Termenilor și Condițiilor și cerința de deduplicare a aceluiași produs între 3 retaileri), am selectat **JD Sports (`jdsports.ro`)**, **Sizeer (`sizeer.ro`)** și **Buzz Sneakers (`buzzsneakers.ro`)**, respingând `zara.com` (interdicție ToS / WAF / brand unic).
3. **Frecvența de verificare (Polling interval):** **57,2%** dintre respondenți verifică manual prețurile zilnic (**28,6%** de mai multe ori pe zi și **28,6%** o dată pe zi), iar **28,6%** de 2–3 ori pe săptămână. Prin urmare, un interval automat de verificare la **6 ore** (de 4 ori pe zi) acoperă nevoile utilizatorilor fără a suprasolicita serverele magazinelor.
4. **Reguli de alertare:** **57,1%** cumpără la scăderea prețului sub un prag fix, **57,1%** la o reducere procentuală de minim 15–20%, iar **28,6%** la revenirea în stoc. **100%** dintre respondenți preferă alertele pe **Email** (85,7% exclusiv Email, 14,3% Email + Telegram).
5. **Istoricul de prețuri:** **85,7%** (71,4% nota maximă 5/5 + 14,3% nota 4/5) consideră foarte important să vadă un grafic al istoricului de preț din ultimele săptămâni/luni (util și pentru a detecta reducerile artificiale).

---

## 2. Rezultatele detaliate ale chestionarului (7 răspunsuri)

### Întrebarea 1: Ce tipuri de produse sau oferte urmărești cel mai des online înainte de a cumpăra / închiria? *(răspuns multiplu)*
- **Haine / Încălțăminte / Articole sportive:** 5 răspunsuri (71,4%)
- **Telefoane / Gadget-uri / Electrocasnice:** 3 răspunsuri (42,9%)
- **Componente PC / Laptopuri / Periferice:** 2 răspunsuri (28,6%)
- **Chirii / Imobiliare:** 2 răspunsuri (28,6%)
- **Bilete de avion / Vacanțe / Bilete la evenimente:** 2 răspunsuri (28,6%)
- **Machiaje:** 2 răspunsuri (28,6%)
- **Cărți / Manuale / Cursuri:** 1 răspuns (14,3%)
- **Parfumuri:** 1 răspuns (14,3%)

### Întrebarea 2: Numește 3–5 site-uri pe care intri cel mai des pentru a verifica sau compara prețurile din categoriile alese mai sus
- *Răspuns 1:* Notino, eMAG, Sephora, Douglas, Dm
- *Răspuns 2:* eMAG, Altex, JD
- *Răspuns 3:* eMAG, Altex, Notino, Zalando, PCGarage
- *Răspuns 4:* Zara, Skyscanner, Kiwi, Stradivarius
- *Răspuns 5:* eMAG, iStyle, Vinted, Zara, Altex
- *Răspuns 6:* EMag, Vinted, Altex

### Întrebarea 3: Cât de des verifici manual prețul sau disponibilitatea unui produs pe care ți-l dorești?
- **De mai multe ori pe zi:** 2 răspunsuri (28,6%)
- **O dată pe zi:** 2 răspunsuri (28,6%)
- **De 2–3 ori pe săptămână:** 2 răspunsuri (28,6%)
- **Doar ocazional:** 1 răspuns (14,3%)
- **O dată pe săptămână:** 0 răspunsuri (0%)

### Întrebarea 4: Ce te determină să iei decizia imediată de a cumpăra / rezerva? *(răspuns multiplu)*
- **Scăderea prețului sub un prag fix stabilit de mine:** 4 răspunsuri (57,1%)
- **O reducere procentuală semnificativă (minim 15–20% față de prețul obișnuit):** 4 răspunsuri (57,1%)
- **Revenirea în stoc a unui produs care era epuizat:** 2 răspunsuri (28,6%)
- **Faptul că prețul începe să crească pe alte site-uri:** 0 răspunsuri (0%)

### Întrebarea 5: Prin ce canal ai prefera să primești o alertă instantă atunci când prețul scade sau produsul revine în stoc?
- **Email:** 6 răspunsuri (85,7%)
- **Ambele (Email + Telegram):** 1 răspuns (14,3%)
- **Mesaj pe Telegram (exclusiv):** 0 răspunsuri (0%)
- **Doar să văd notificarea când intru în aplicație:** 0 răspunsuri (0%)

### Întrebarea 6: Cât de important este pentru tine să vezi un istoric grafic al prețului din ultimele săptămâni/luni? *(scară 1–5)*
- **Nota 5 (Foarte important):** 5 răspunsuri (71,4%)
- **Nota 4:** 1 răspuns (14,3%)
- **Nota 3:** 0 răspunsuri (0%)
- **Nota 2:** 1 răspuns (14,3%)
- **Nota 1 (Deloc important):** 0 răspunsuri (0%)

### Întrebarea 7: Ce te frustrează cel mai mult atunci când urmărești prețuri sau oferte pe internet în prezent?
- *„Am prea multe tab-uri deschise”*
- *„Pierd timpul deschizând 5 tab-uri zilnic”*
- *„Aflu prea târziu că un produs a avut o reducere semnificativă”*
- *„Verific produsul și după nu mai este în stoc”*
- *„Derutarea prețului prin tot felul de oferte dar și taxe ascunse”*
- *„Pierd mult timp verificând prețurile pe diferite platforme”*

