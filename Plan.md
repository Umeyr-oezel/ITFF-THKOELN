---

 Hinweis: Aufgabe 1 könnte änderungen bekommen. Diese ist unabhängig von den restlichen Aufgaben.

---
# Plan.md - ITFF-THKOELN Projektplan

> **Hinweis fuer Claude:** Lies diese Datei vor JEDEM Arbeitsschritt.
> Wenn ein Nutzer seinen Namen nennt, weisst du sofort welches Team
> und welche Aufgaben relevant sind. Halte dich strikt an diesen Plan.
>
> Der vorherige Plan (Django-Umstellung, Hardcoded-Werte, Historie 2020-2025)
> ist abgeschlossen und liegt unter `notes/Plan_archiv.md`. Dieser Plan
> baut darauf auf und deckt die naechste Projektphase ab: Praesentation,
> Code-Review, Server-Recherche (Plan B) und die finale DB-Migration.

---

## Teams

| Team | Mitglieder | Aufgaben |
|------|-----------|----------|
| Team 1 | Emil, Umeyr | Aufgabe 1 (Praesentation, Skript, Grafiken/README) |
| Team 2 | Kenan, Matthias | Aufgabe 2 (Code-Review datei-fuer-datei), Aufgabe 3 (Plan-B-Recherche Server), Aufgabe 4 (DB-Migration) |
| Alle | Emil, Umeyr, Kenan, Matthias | Abschluss-Durchsprache vor Abgabe/Praesentation |

---

## Aufgabe 1: Praesentation (Team 1 - Emil & Umeyr)

Eine kurze, klare Praesentation des Projekts (PowerPoint oder gleichwertig)
mit genau **4 Folien**, dazu ein ausgearbeitetes Sprech-Skript und verbesserte
Grafiken, die in die `README.md` und die Output-Struktur eingebunden werden.

### 1.1 Foliengeruest (4 Folien)
- [ ] Inhalt pro Folie festlegen (Vorschlag, im Team abstimmen):
  - **Folie 1 - Projekt & Ziel:** Worum geht es (SEC-Insider-Transaktionen, Form 4), Fragestellung, Teamaufteilung
  - **Folie 2 - Architektur/Pipeline:** Download -> Parser -> Aufbereitung -> Validierung -> DB (Django/PostgreSQL) -> Evaluation
  - **Folie 3 - Ergebnisse:** Kennzahlen (4,6 Mio. Zeilen, 2020-2025, Validierungsquoten) + die besten Charts
  - **Folie 4 - Stand & Ausblick:** SQLite-Fallback, offene Punkte (PostgreSQL-Server), Plan A/Plan B, naechste Schritte
- [ ] Tool festlegen (PowerPoint / Google Slides / LibreOffice Impress)

### 1.2 Praesentation erstellen
- [ ] 4 Folien gemaess Geruest bauen
- [ ] TH-Koeln-Logo aus `assets/` einbinden (`th_koeln_logo_rgb.png`)
- [ ] Einheitliches Layout/Design ueber alle Folien
- [ ] Datei im Repo ablegen (Ordner `Documents/` fuer die Praesentation)

### 1.3 Praesentationsskript
- [ ] Sprechtext je Folie ausarbeiten (was wird zu jeder Folie gesagt)
- [ ] Rollen-/Redeverteilung zwischen Emil & Umeyr festlegen
- [ ] Zeitrahmen einplanen und einmal proben
- [ ] Skript im Repo ablegen (`Documents/` oder `docs/`)

### 1.4 Grafiken verbessern & einbinden
- [ ] Aussagekraeftigste Charts aus `output/<Jahr>/charts/` auswaehlen
- [ ] Grafiken verbessern (Titel, Achsenbeschriftung, Lesbarkeit, ggf. Farben/`CHART_COLORS`)
  <!-- Falls Anpassungen am Chart-Code noetig sind: nur in Absprache mit Team 2 (Code-Review), um Konflikte zu vermeiden. -->
- [ ] Ausgewaehlte Grafiken in die `README.md` einbetten
- [ ] Output-Struktur (`output/<Jahr>/charts|tables|report`) in der `README.md` erklaeren
- [ ] Ggf. neu generieren, falls Charts angepasst wurden

### 1.5 Dokumentation
- [ ] Unter `/docs` dokumentieren: `praesentation.md` (Aufbau, Skript-Verweis, verwendete Grafiken)

---

## Aufgabe 2: Code-Review (Team 2 - Kenan & Matthias)

Systematisches Review **datei fuer datei** - nicht allgemein. Pro Datei werden
drei Dinge geprueft: **Effizienz** (unnoetige Schleifen/DB-Roundtrips,
bessere Struktur), **Hardcoded-Werte** (gehoeren sie nach `config.py`/`.env`?)
und **Bugs** (Logikfehler, Edge Cases). Gefundene Punkte werden behoben und
pro Datei dokumentiert.

### 2.1 Vorgehen je Datei
Fuer jede Datei jeweils:
- Effizienz pruefen und verbessern
- Hardcoded-Werte aufspueren und (nach Absprache) auslagern
- Bugs finden und fixen
- Aenderung kurz festhalten (welche Datei, was geaendert, warum)

### 2.2 Root-Dateien
- [ ] `config.py`
- [ ] `main.py`
- [ ] `manage.py`

### 2.3 modules/
- [ ] `modules/__init__.py`
- [ ] `modules/downloader.py`
- [ ] `modules/parser.py`
- [ ] `modules/data_preparation.py`
- [ ] `modules/db_manager.py`
- [ ] `modules/validation.py`
- [ ] `modules/evaluation.py`

### 2.4 Django (pipeline/ + secpipeline/)
- [ ] `pipeline/models.py`
- [ ] `pipeline/admin.py`
- [ ] `pipeline/apps.py`
- [ ] `pipeline/views.py`
- [ ] `secpipeline/settings.py`
- [ ] `secpipeline/urls.py`
- [ ] `pipeline/tests/` (Tests pruefen, ggf. erweitern)

### 2.5 Querschnitt (ueber alle Dateien)
- [ ] Keine ungenutzten Imports/Variablen (`pyflakes`/`py_compile` sauber)
- [ ] Einheitlicher Code-Stil (PEP-8, Englisch, Docstrings vorhanden)
- [ ] Keine neuen Hardcoded-Werte; bewusste Ausnahmen kommentieren
- [ ] Bugfixes durch Unit-Tests absichern (`python manage.py test` bleibt gruen)

### 2.6 Dokumentation
- [ ] Unter `/docs` dokumentieren: `code_review.md` (Befunde + Fixes je Datei)

---

## Aufgabe 3: Plan-B-Recherche - Server-Alternative (Team 2 - Kenan & Matthias)

Plan A ist der Uni-Server von Herrn Miebs. Falls die Uni diesen nicht
bereitstellt, brauchen wir einen **Plan B**: ein eigener Server mit
**PostgreSQL-Datenbank**, **kostenlos** und **ohne Benachteiligung**
(gleiche Funktionalitaet, keine harten Limits, die das Projekt einschraenken).

### 3.1 Anforderungen festlegen
- [ ] Kostenlos (dauerhaft Free-Tier, keine Kreditkarten-Falle)
- [ ] Vollwertige PostgreSQL-Datenbank (Version, Speicherplatz)
- [ ] Keine Benachteiligung: ausreichend Speicher/Verbindungen, kein automatisches
  Pausieren/Loeschen, das den Pipeline-Lauf (4,6 Mio. Zeilen) blockiert
- [ ] Datenschutz/Standort beruecksichtigen (moeglichst EU)
- [ ] Erreichbar von ausserhalb (fuer den Pipeline-Import per Django)

### 3.2 Optionen recherchieren
- [ ] Kandidaten sammeln und pruefen (Startpunkte, zu verifizieren):
  Neon, Supabase, Railway, Render, Aiven (Free), ElephantSQL, Fly.io Postgres
- [ ] Vergleichstabelle erstellen: Kosten, Speicher, Verbindungslimits,
  PostgreSQL-Version, Auto-Pause, Standort, Einrichtungsaufwand
- [ ] Kurz testen, ob Django sich verbinden kann (Test-Instanz)

### 3.3 Entscheidung & Doku
- [ ] Empfehlung fuer Plan B festhalten (1 Favorit + 1 Reserve)
- [ ] Mit Team und ggf. Betreuer abstimmen (keine eigenmaechtige Festlegung)
- [ ] Unter `/docs` dokumentieren: `plan_b_server.md`

---

## Aufgabe 4: DB-Migration (Team 2 - Kenan & Matthias)

Die eigentliche Migration auf den echten PostgreSQL-Server. **Wartet**, bis
der Server steht (Plan A oder Plan B) und Zugangsdaten vorliegen. Bis dahin
laeuft alles weiter ueber den SQLite-Fallback.

### 4.1 Voraussetzungen (blockiert bis erfuellt)
- [ ] Server steht (Plan A: Herr Miebs **oder** Plan B aus Aufgabe 3)
- [ ] PostgreSQL-Zugangsdaten liegen vor

### 4.2 Migration durchfuehren
- [ ] Echte PostgreSQL-Zugangsdaten in `.env` eintragen (Platzhalter ersetzen)
- [ ] `migrate` gegen PostgreSQL ausfuehren - alle 7 Tabellen identisch erzeugen
- [ ] Identischer End-to-End-Lauf 2020-2025 gegen PostgreSQL (wie SQLite-Lauf)
- [ ] Validierung gegen PostgreSQL gegenpruefen (gleiche Quoten wie SQLite)
- [ ] Evaluation/Charts gegen PostgreSQL erzeugen und vergleichen

### 4.3 Performance (war im alten Plan offen)
- [ ] Langsame Queries auf PostgreSQL identifizieren (Profiling)
- [ ] Speicherverbrauch bei grossen Datenmengen pruefen

### 4.4 Dokumentation
- [ ] Unter `/docs` dokumentieren: `postgres_migration.md` (Ablauf + Vergleich SQLite/PostgreSQL)

---

## Quellen

Diese Quellen werden im Projekt verwendet. Keine anderen ohne Absprache:

- **SEC EDGAR Insider Transactions:** `https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets`
- **SEC Form 4 Dokumentation:** Die `FORM_345_readme.htm` und `FORM_345_metadata.json` aus den ZIP-Archiven
- **Python-Pakete:** Nur die in `requirements.txt` gelisteten
- **Server-Recherche (Aufgabe 3):** Anbieter-Webseiten/Doku der geprueften PostgreSQL-Hoster (nur zur Recherche, keine neue Datenquelle fuer die Pipeline)

---

## Aenderungsprotokoll

| Datum | Aenderung | Begruendung |
|-------|-----------|-------------|
| 14.06.2026 | Neuer Plan fuer die naechste Phase erstellt; alter Plan nach `notes/Plan_archiv.md` archiviert | Django-Umstellung, Hardcoded-Werte und Historie 2020-2025 sind abgeschlossen; jetzt folgen Praesentation, Code-Review, Server-Plan-B und finale DB-Migration (Absprache mit Umeyr) |
| 14.06.2026 | Aufgaben-Zuordnung: Team 1 = Praesentation; Team 2 = Code-Review, Plan-B-Recherche, DB-Migration | Praesentation/Doku in einer Hand (Team 1), Technik/Infrastruktur/Migration in einer Hand (Team 2) zur Vermeidung von Konflikten (Absprache mit Umeyr) |
