# Claude Code — maximales Potenzial ausschöpfen

## 0. Grundprinzipien

Claude Code startet jede Session mit leerem Kontext. Alles was Claude wissen soll, muss aktiv geladen werden. Das Grundprinzip: **weniger ist mehr.** Claude hat effektiv 100–150 nutzbare Instruktions-Slots — jede überflüssige Zeile verdrängt eine wichtige.

---

## 1. CLAUDE.md — das Herzstück

Schreib sie einmal, halte sie unter 120 Zeilen, ergänze sie nur wenn etwas wirklich in jeder Session gebraucht wird.

**Was hineingehört:**
- Tech Stack, Projektstruktur, Build- und Test-Befehle
- Arbeitsweise: was Claude selbstständig darf, was mit dir besprochen wird
- Code-Philosophie: Effizienz und Lesbarkeit vor Komplexität
- Verweis auf `PLAN.md` — Claude prüft zu Sessionbeginn den aktuellen Stand
- Design-Entscheidungen (Architektur, ggf. Frontend)
- Verfügbare MCP-Tools, mit Hinweis dass weitere Tools besprechbar sind
- Keine generischen Regeln wie "schreib sauberen Code"

**Was nicht hineingehört:**
- Alles was nur gelegentlich gebraucht wird → gehört in `docs/` und wird per `@docs/dateiname.md` bei Bedarf geladen

---

## 2. PLAN.md — strukturiertes Projektmanagement

**Aufbau:**
Phase 1 — Setup & Grundarchitektur
[ ] Phase 1.1 — Datenbankschema
[ ] Phase 1.2 — API-Grundstruktur
[ ] Phase 1.3 — Unit Tests Phase 1
[ ] Phase 1.4 — Phasentest & Bugsuche
Phase 2 — Kernfunktionalität
...
Phase N — Abschluss & Modulreview

**Regeln:**
- Jede Teilphase hat eine Checkbox — Claude pflegt diese strikt
- Max. 2 Teilphasen ohne deine Interaktion
- Planänderungen als Kommentar ergänzen, alter Plan ~~durchgestrichen~~ aber nicht gelöscht
- Tools und Libraries hier festhalten
- Unit Tests und Phasentests sind explizite Teilphasen, keine Nachgedanken
- Nach jeder Phase: Bugsuche — Critical & Hard aktiv fixen, Mid/Soft nur wenn zufällig gefunden
- Planänderungen werden als Kommentar ergänzt, alter Plan durchgestrichen aber nicht gelöscht

---

## 3. Kontextmanagement

- `/clear` für neue Aufgaben, nie mitten in einer Teilphase
- Session-Wechsel nur an sauberen Phasengrenzen — Claude aktualisiert `PLAN.md` vorher
- `/compact` sparsam — dauert über eine Minute, kostet Arbeitszeit
- Bei langen Sessions: `/clear` + Kontext über `PLAN.md` und `@docs/`-Referenzen neu aufbauen
- `ultrathink` für Architekturentscheidungen die tiefes Reasoning brauchen

---

## 4. Finale Phase — Modulreview

**Aufbau:**
Phase N — Abschluss
[ ] Phase N.1 — Review Modul A (z.B. Auth & User)
[ ] Phase N.2 — Review Modul B (z.B. API-Layer)
[ ] Phase N.3 — Review Modul C (z.B. Datenbank & Queries)
[ ] Phase N.4 — Gesamte Test-Suite durchlaufen
[ ] Phase N.5 — PLAN.md als abgeschlossen markieren

Pro Modul: Bugs, Redundanzen, Performance-Auffälligkeiten. Nicht jede Datei — jedes Verantwortungsgebiet.

---

## 5. Drei Faustregeln gegen Overhead

1. **Wenn du etwas zweimal erklärst** → gehört es in `CLAUDE.md` oder `PLAN.md`
2. **Wenn du zögerst den Chat zu erneuern** → tue es trotzdem, saubere Übergänge sind wichtiger als Bequemlichkeit
3. **Wenn die `CLAUDE.md` über 120 Zeilen geht** → kürzen, nicht erweitern
