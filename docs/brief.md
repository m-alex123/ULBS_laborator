# P23 · Monitor de prețuri cu scraping etic
Categoria E · Integrări & fișiere · Dificultate ★★★ · Efort estimat ~34h · Runda 1 · 1 student

## Pe scurt
Urmăritor de prețuri și disponibilitate pentru o nevoie reală (manuale, chirii în orașul tău, bilete, componente, un produs anume) pe minim 3 site-uri, cu adaptoare, istoric, alerte, respectarea robots.txt și detecția adaptoarelor stricate.

## Input uman obligatoriu
O nevoie reală a unor oameni reali: intervievezi 5 persoane despre ce urmăresc (chirii? laptopuri? bilete?), cât de des verifică, ce le-ar declanșa o decizie. Alegi categoria și cele minim 3 site-uri pe baza lor. Analiza de legalitate și etică scrisă (ETHICS.md): termenii fiecărui site, robots.txt, frecvența acceptabilă, ce date stochezi, de ce e ok. Dacă un site interzice explicit, nu-l folosești și documentezi. INTERVIEW.md + ETHICS.md.

## Context real
Oamenii verifică manual aceleași 5 pagini în fiecare zi. Site-urile își schimbă HTML-ul fără să anunțe. Un scraper scris "să meargă" se strică în 2 săptămâni și nimeni nu știe.

## Cerințe funcționale (must)
- Lista de urmărire per utilizator: URL-uri de produse / căutări, cu nume și prag.
- Adaptoare per site (minim 3), fiecare cu: extragere preț, monedă, disponibilitate, titlu, imagine; testate pe HTML salvat în repo (fixtures).
- Programare: fiecare adaptor rulează la interval configurabil, cu politețe: respectă robots.txt (verificat în cod, nu doar în document), delay între cereri, User-Agent identificabil, limită de cereri pe oră per domeniu.
- Istoric de prețuri cu grafic, minim / maxim / medie, procent față de ultima verificare.
- Alerte: pe email și Telegram (bot), la scădere sub prag, la revenirea în stoc, la creștere bruscă.
- Deduplicare între site-uri: același produs pe 3 site-uri e o singură intrare, cu comparație și "cel mai ieftin acum".
- Panou de sănătate a adaptoarelor: rata de succes, ultima rulare, erori, "selectorul pare schimbat" cu snapshot-ul HTML pentru debugging.
- Roluri: utilizator, admin (adaptoare, limite).

## Cerințe tehnice specifice
- Coadă de job-uri cu worker separat; retry cu backoff; un site picat nu blochează restul.
- Parsarea prețurilor e o funcție pură testată pe cazuri reale: "1.299,99 lei", "de la 49 RON", "1 299 lei", preț tăiat + preț redus, "indisponibil".
- Snapshot-ul HTML al ultimei rulări eșuate se păstrează (object storage) pentru fiecare adaptor.
- Integrarea Telegram primește și comenzi (/list, /add <url>), prin webhook sau long polling.

## Twist: să știi că te-ai stricat înainte să-ți spună utilizatorii
Un adaptor care nu aruncă eroare dar extrage 0 lei sau titlul greșit e mai rău decât unul care crapă. Implementezi detecția derivei: validări de plauzibilitate (prețul nu scade cu 95% într-o zi, titlul seamănă cu cel anterior, câmpurile obligatorii sunt prezente), compararea cu rularea anterioară și marcarea adaptorului ca "suspect" cu alertă către admin, fără să trimiți alerte false utilizatorilor. Deduplicarea între site-uri trebuie să reziste la titluri diferite pentru același produs (normalizare, EAN / model când există, confirmare manuală pentru incert). Totul sub politica de politețe, demonstrabilă din log-uri.

## Variabilele tale
- Categoria și cele 3 site-uri (cu analiza de etică).
- Intervalul de verificare per site, justificat.
- Pragurile de plauzibilitate pentru detecția derivei.

## Definition of Done
- Cele 3 adaptoare rulează pe live de minim 10 zile; istoricul e vizibil.
- Parsarea prețurilor are minim 10 teste pe formate reale.
- Alerta Telegram funcționează și botul răspunde la /list.
- Un adaptor stricat intenționat (schimbi selectorul) e detectat ca suspect, fără alerte false.
- ETHICS.md e complet și robots.txt e verificat în cod (test).

## La susținere te întrebăm
- Cum decizi că un adaptor "pare stricat" deși nu a aruncat nicio eroare?
- Cum potrivești "Laptop ASUS X515 15.6" de pe un site cu "ASUS VivoBook X515EA" de pe altul?
- Ce ai refuzat să faci din motive etice și de ce?
