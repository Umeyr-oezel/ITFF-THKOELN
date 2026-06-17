# Presentation Script (Example) — Advisory Board, English

> Beispiel-Sprechskript fuer die englische Beirats-Praesentation (Aufgabe 1).
> **Keine festen Texte** — Talking Points + Beispiel-Formulierungen zum Anpassen.
> Aufbau: 4 Folien, ~4-5 Min je Folie (~20 Min + Q&A). Sprecher: Emil / Umeyr.
> Design-Leitlinie (Beirat): eine Kernaussage pro Folie, wenig Kontext,
> mit dem Haken starten, mit "so what" + naechsten Schritten enden.

---

## Slide 1 — Hook: "When the market crashed, insiders bought"
**Visual:** `sentiment_all_time.png`

**Goal:** grab attention in 30 seconds and motivate *why insider data matters*.

**Talking points (example phrasing):**
- Set the scene: *"March 2020. Markets are in free fall — the S&P 500 drops about a third in a few weeks. The question we asked: what did the people who run these companies do with their own money?"*
- Reveal the chart: *"Each bar is one month. It shows the share of insider trades that were purchases. In a normal month that's about 22%. In March 2020 it hit 55% — the single most bullish month in six years."*
- The point: *"Insiders disclose every trade to the SEC on a Form 4. That's a public signal of conviction. Our project turns 4.6 million of those filings into something you can read at a glance."*
- Thesis in one line: *"Insider filings are a window into conviction — we built the pipeline that opens it."*

**Transition:** *"To get from raw regulatory filings to this chart, we built a data pipeline. Here's the architecture."*

---

## Slide 2 — System Architecture
**Visual:** `system_pipeline.png` (seaborn) — optional: pair with the flow diagram `system_architecture.png`

**Goal:** show the end-to-end system at a high level; convey scale and robustness.

**Talking points:**
- Source: *"One source — the SEC EDGAR Form 4 data sets, quarter by quarter, 2020 to 2025."*
- Walk the flow once: *"Six phases — download, parse, prepare, load, validate, evaluate — and the whole thing runs with a single command."*
- Robustness: *"It's idempotent: you can re-run it any time and never get duplicates."*
- Scale: *"4.6 million rows, seven tables, about twenty minutes end to end."*
- Key design choice: *"It's database-agnostic — PostgreSQL in production, SQLite on a laptop, exactly the same code."*

**Transition:** *"That's the data flow. One quick look at how the code is organised — then straight to the findings."*

---

## Slide 3 — Code Architecture (keep it light!)
**Visual:** `code_layers.png` (seaborn) — optional: pair with the layer diagram `code_architecture.png`

**Goal:** signal clean engineering — **not** a deep dive. Target ~2 minutes.

**Talking points (short):**
- Four layers: *"Orchestration on top, the pipeline logic in the middle, a Django persistence layer, and a foundation of configuration and tests."*
- Two principles, one sentence each: *"No hardcoded values — everything lives in config and .env. And it's tested — 30 unit tests run against a throwaway SQLite database."*
- Why the board should care: *"This is what lets the project outlive the course: maintainable, and the database is swappable."*
- ⚠️ Do **not** go function by function. Resist the detail.

**Transition:** *"With that foundation in place, here's what the data actually told us."*

---

## Slide 4 — Results (the 2 strong images) + so what
**Visuals:** `trend_all_time.png` and `covid_buyers.png`

**Goal:** deliver the payoff, show rigour, end with next steps.

**Talking points:**
- Image 1 (trend): *"Across six years, insiders sell roughly three times more often than they buy — selling is the norm. Against that baseline, the early-2020 jump in buying really stands out."*
- Image 2 (who bought): *"And it wasn't noise. The most active buyers in March 2020 were real, substantial companies — International Flavors with 157 purchases, TransDigm with 121, RBB Bancorp, Five Point."*
- Rigour / credibility note: *"One honest caveat: we report transaction counts, not dollar volume. Our own validation flagged micro-cap filings with impossible dollar values, so counts are the trustworthy measure — and tightening that check is on our roadmap."*
- So what + next steps (board-relevant): *"Next: a production database — the university server as Plan A, a free hosted PostgreSQL as Plan B — then the full migration, tighter validation, and analysis across more market events."*
- Close with a callback: *"Insider filings are a signal. In March 2020, that signal was simple: buy."*

---

## Delivery notes
- **Roles:** decide who presents which slide (e.g. Umeyr: 1 + 4, Emil: 2 + 3).
- **Timing:** rehearse once end-to-end; slide 3 is the one to keep short.
- **Likely Q&A:**
  - *"Are the dollar figures wrong?"* — For micro-caps, yes; that's exactly why we use counts.
  - *"Could the insiders simply be wrong?"* — We measure behaviour, not outcomes; the signal is conviction, not a guarantee.
  - *"How reliable is the source?"* — Official, mandatory SEC filings (Form 4).
