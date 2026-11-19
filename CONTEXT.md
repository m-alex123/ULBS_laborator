# CONTEXT — ULBS_laborator vocabulary

<!-- graffino-agentic:begin v1 -->
> The approved terms for this project. Use each term exactly as defined, in the part
> of speech given. Never swap in a synonym; never use a word on an _Avoid_ line.
<!-- graffino-agentic:end -->

**Laborator** (noun) — Practical laboratory assignment, coursework session, or exercise.
_Avoid_: lab, experiment, workshop.

**Student** (noun) — Individual enrolled in the university course completing the assignments.
_Avoid_: pupil, participant, learner.

**Assignment** (noun) — Defined problem statement or task set by the instructor to be implemented.
_Avoid_: homework, tasklet, ticket.

**Submission** (noun) — Completed solution or deliverable pushed to the repository for evaluation.
_Avoid_: turn-in, delivery, upload.

**Requirement** (noun) — Specific functional or academic condition that the implementation must satisfy.
_Avoid_: spec, demand, prerequisite.

## Project P23 Domain Vocabulary

**SKU** (noun) — Stock Keeping Unit; the standardized manufacturer model identifier used to correlate and deduplicate identical footwear items across multiple supported retailers.
_Avoid_: product code, item id, barcode, article number, internal ref.

**Canonical Product** (noun) — The central, store-agnostic footwear entity identified by a unique SKU and brand, aggregating multiple retailer listings and unified price history.
_Avoid_: master product, global item, base shoe, unified article, parent product.

**Product Listing** (noun) — A retailer-specific product entry on a supported store (JD Sports, Sizeer, or Buzz Sneakers) tied to a canonical product, holding store URL, current price, raw title, and stock status.
_Avoid_: retailer item, store page, offer page, crawled product.

**Polite Polling** (noun) — Scheduled, respectful scraping mechanism adhering to `robots.txt`, enforcing a minimum 10-second delay between requests per domain, at most 30 requests/hour per domain, and a 6-hour default polling interval with a transparent User-Agent.
_Avoid_: crawling, aggressive scraping, background sync, web spidering, rapid polling.

**Circuit Breaker** (noun) — An automated safety switch that trips and halts scraping requests to a retailer domain upon consecutive errors, HTTP 429/5xx responses, or anti-bot blocks to protect target servers and avoid IP bans.
_Avoid_: error blocker, fail-safe trip, request killswitch, pause mode, breaker switch.

**Drift Detection** (noun) — Heuristic verification that flags parsed data as suspect and suppresses user notifications when extreme price swings (>70% drop, >200% rise, or price <50 RON), title similarity drops below 60%, or missing required fields indicate website HTML layout changes.
_Avoid_: anomaly detection, price check, error sniffing, schema validation, outlier detection.

**Watchlist** (noun) — A user's personalized collection of canonical products being monitored, configured with custom alert triggers such as target price thresholds, minimum percentage discounts, and stock availability notifications.
_Avoid_: favorites, wishlist, bookmarks, tracking list, saved items, cart.

**Snapshot** (noun) — A timestamped, local HTML file saved in `storage/snapshots/` when an adapter encounters an error or triggers drift detection, retained for offline debugging and administrative inspection.
_Avoid_: page dump, cached page, html backup, raw response, page capture.
