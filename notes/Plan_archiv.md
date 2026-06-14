# Plan.md - ITFF-THKOELN Projektplan

> **Hinweis fuer Claude:** Lies diese Datei vor JEDEM Arbeitsschritt.
> Wenn ein Nutzer seinen Namen nennt, weisst du sofort welches Team
> und welche Aufgaben relevant sind. Halte dich strikt an diesen Plan.

---

## Teams

| Team | Mitglieder | Aufgaben |
|------|-----------|----------|
| Team 1 | Emil, Umeyr | Aufgabe 1 (Setup), Aufgabe 2 (Django-Umstellung), Aufgabe 3 (Docstrings) |
| Team 2 | Kenan, Matthias | Aufgabe 1 (Setup), Aufgabe 4 (Hardcoded → Flexibel), Aufgabe 5 (Historie erweitern) |
| Alle | Emil, Umeyr, Kenan, Matthias | Aufgabe 6 (Code Review / Bugsuche) |

---

## Aufgabe 1: Setup (Alle Teams)

Grundlegende Einrichtung bevor es losgeht.

- [x] Repository klonen und lokale Umgebung einrichten
- [x] `requirements.txt` installieren (`pip install -r requirements.txt`)
- [x] `.env` Datei lokal anlegen (Vorlage: `.env.example`)
- [ ] Datenbank-Credentials eintragen sobald vorhanden
  - Zugangsdaten werden **lokal in `.env` gespeichert**, niemals auf GitHub
  - `.env` ist in `.gitignore` eingetragen
  - Aktuell Platzhalter in `.env` (siehe Abschnitt 2.8), echte Werte folgen mit PostgreSQL-Zugang
- [x] Pipeline einmal lokal testen (`python main.py`)
  <!-- Erledigt 04.06.2026 ueber den SQLite-Fallback: kompletter Lauf 2020-2025,
       4.612.977 Zeilen, 0 Fehler. Gegen PostgreSQL weiterhin offen (kein Zugang). -->
- [ ] Identischer End-to-End-Lauf gegen PostgreSQL (blockiert bis Zugang da ist)

---

## Aufgabe 2: Django-Umstellung (Team 1 - Emil & Umeyr)

Umstellung von rohem SQL (SQLAlchemy + MySQL) auf Django ORM mit PostgreSQL.

### 2.1 Django-Projekt initialisieren
- [x] Django zu `requirements.txt` hinzufuegen (`django>=5.2,<6.0`, `psycopg2-binary`)
- [x] Django-Projekt erstellen (`django-admin startproject secpipeline .`)
- [x] Django-App fuer die Pipeline erstellen (`pipeline`)
- [x] `settings.py` konfigurieren: PostgreSQL-Verbindung ueber `.env`
- [x] `.env.example` aktualisieren mit neuen DB-Feldern (`DB_ENGINE`, `DB_NAME`)

### 2.2 Django-Models definieren
- [x] Model `Submission` erstellen (entspricht Tabelle `submissions`)
  - Felder: `accession_number` (PK), `filing_date`, `issuer_cik`, `issuer_name`, `issuer_ticker`, `rptowner_cik`, `rptowner_name`, `is_director`, `is_officer`, `is_ten_percent`, `is_other`, `officer_title`, `created_by`, `source_quarter`, `created_at`
- [x] Model `NonderivTrans` erstellen (entspricht `nonderiv_trans`)
  - FK zu `Submission` via `accession_number` mit `CASCADE`
  - Felder: `trans_date`, `trans_code`, `equity_swap`, `shares`, `price_per_share`, `shares_owned_following`, `nominal_volume`, `is_valid`, `validation_flags`, `created_by`, `source_quarter`, `created_at`
- [x] Model `NonderivHolding` erstellen (entspricht `nonderiv_holdings`)
- [x] Model `DerivTrans` erstellen (entspricht `deriv_trans`)
- [x] Model `DerivHolding` erstellen (entspricht `deriv_holdings`)
- [x] Model `ValidationLog` erstellen (entspricht `validation_log`)
- [x] Model `PipelineLog` erstellen (entspricht `pipeline_log`)
- [x] Indizes in `Meta.indexes` definieren (gleiche Indizes wie aktuell)
- [x] Migrations erstellen (`makemigrations` -> `0001_initial.py`)
  <!-- `migrate` (Ausfuehrung gegen die DB) erst moeglich, sobald PostgreSQL-Zugangsdaten vorliegen -->
- [x] Migrations ausfuehren (`migrate`)
  <!-- Auf SQLite-Fallback ausgefuehrt: alle 7 Tabellen sauber erzeugt.
       Gegen PostgreSQL noch offen (kein Zugang). -->

### 2.3 db_manager.py umschreiben
- [x] `get_engine()` entfernen - Django verwaltet die Verbindung
- [x] `setup_database()` entfernen - Django Migrations uebernehmen das
- [x] `CREATE_TABLES` SQL entfernen - durch Django Models ersetzt
- [x] `_try_add_foreign_keys()` entfernen - Django setzt FKs automatisch
- [x] `import_quarter()` umschreiben auf Django ORM (`bulk_create`, `filter().delete()`)
- [x] `_delete_quarter()` umschreiben auf Django ORM
- [x] `_execute_with_retry()` anpassen oder entfernen
  <!-- Entfernt: war ein Workaround fuer Lock-Timeouts auf dem geteilten MySQL-Server; auf eigener PostgreSQL-DB nicht noetig. Import laeuft jetzt in einer Transaktion (transaction.atomic) pro Quartal. -->
- [x] `log_pipeline_run()` umschreiben auf `PipelineLog.objects.create()`
- [x] Idempotenz beibehalten: Delete-then-Insert Strategie
- [x] `pipeline_log` wird weiterhin NIE geloescht
- [x] Import filtert Orphan-Zeilen vorab raus und loggt sie (Absprache mit Emil, wegen echtem FK)

### 2.4 validation.py anpassen
- [x] SQL-Queries durch Django ORM ersetzen (`filter`, `annotate`, `F()`)
- [x] `_update_main_table()` umschreiben auf `bulk_update()`
- [x] `_write_validation_log()` umschreiben auf `bulk_create()`
- [x] `_validate_table()` - LEFT JOIN durch Django `select_related` oder Raw-Query ersetzen
  <!-- Geloest ueber values("submission__filing_date") - die FK-Beziehung erzeugt den Join. -->
- [x] Alle 8 Validierungschecks muessen identisch funktionieren
  <!-- Die 8 Check-Funktionen sind unveraendert (arbeiten auf DataFrame). Der Orphan-Check bleibt als Sicherheitsnetz: durch echten FK + Orphan-Filter im Import findet er normalerweise nichts mehr. -->
- [x] Numerische Spalten nach ORM-Laden mit `pd.to_numeric` casten (sonst crashen `<0`-Checks bei NULL)

### 2.5 evaluation.py anpassen
- [x] SQL-Queries durch Django ORM ersetzen
- [x] `_get_available_months()` umschreiben
- [x] `query_monthly_ranking()` umschreiben (GROUP BY mit `values().annotate()`)
- [x] `_query_monthly_totals()` umschreiben
- [x] `_get_pipeline_stats()` umschreiben
- [x] `_retry_query()` anpassen oder durch Django Connection-Handling ersetzen
  <!-- Entfernt - war Retry-Logik fuer den geteilten MySQL-Server; Django verwaltet Connections selbst. engine-Parameter aus allen Funktionen entfernt. -->
- [x] MySQL-spezifisches SQL (z.B. `YEAR()`, `MONTH()`) durch Django-Funktionen ersetzen (`ExtractMonth`, `trans_date__year`-Lookup)

### 2.6 Restliche Anpassungen
- [x] `config.py` anpassen: `DB_CONFIG` und `SCHEMA_NAME` durch Django-Settings ersetzen
- [x] `main.py` anpassen: `django.setup()` am Anfang aufrufen (vor allen Modul-Importen)
  <!-- preflight_checks prueft DB jetzt ueber django.db.connection statt SQLAlchemy. setup_database()-Aufruf entfernt (migrate uebernimmt das Schema). -->
- [x] `modules/__init__.py` anpassen: `get_engine()` entfernen
- [x] `pymysql` aus `requirements.txt` entfernen (auch `sqlalchemy`)
- [x] Alte SQLAlchemy-Imports entfernen

### 2.7 Testen
Vorab ohne DB getestet: `python manage.py check` (0 Probleme), `makemigrations`
(0001_initial mit allen 7 Tabellen), `py_compile` aller Module, `python main.py
--help` (django.setup + komplette Import-Kette laden sauber). Der Rest braucht
echten PostgreSQL-Zugang.
<!-- Verifiziert 04.06.2026 auf dem SQLite-Fallback (kompletter Lauf 2020-2025).
     Die identische Pruefung gegen PostgreSQL ist erst nach Zugang moeglich;
     der Code-Pfad ist aber DB-unabhaengig (gleiches ORM, gleiche Migrations). -->
- [x] Migrations laufen fehlerfrei durch (`migrate`) - auf SQLite verifiziert, Postgres offen
- [x] Pipeline laeuft komplett - auf SQLite verifiziert (4,6 Mio. Zeilen, 0 Fehler), Postgres offen
- [x] Datenimport funktioniert idempotent - Unit-Test + 24 `pipeline_log`-Eintraege bei Delete-then-Insert
- [x] Validierung liefert gleiche Ergebnisse - auf SQLite verifiziert (100,0 % / 99,9 % gueltig), Postgres offen
- [x] Evaluation/Charts werden korrekt generiert - 450 Charts, 432 CSVs, 6 PDF-Reports erzeugt
- [x] Unter `/docs` dokumentieren: `django_migration.md`

### 2.8 PostgreSQL-Zugangsdaten
Stand: Die PostgreSQL-Zugangsdaten liegen **noch nicht vor**. Bis dahin wird
ueberall mit Platzhaltern gearbeitet, damit die Umstellung trotzdem vorbereitet
werden kann.

- [x] In `.env` Platzhalter fuer die DB-Zugangsdaten eintragen (`PLATZHALTER_*`)
- [ ] Echte PostgreSQL-Zugangsdaten in `.env` eintragen, sobald sie vorliegen
- [x] `.env.example` auf PostgreSQL-Felder umgestellt (`DB_ENGINE`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`) + SQLite-Fallback dokumentiert
- [x] Geprueft: keine echten Zugangsdaten im Code/GitHub (grep sauber, `.env` in `.gitignore`)

---

## Aufgabe 3: Docstrings vervollstaendigen (Team 1 - Emil & Umeyr)

Jede Funktion und jedes Modul braucht einen Docstring. Bestehende Docstrings beibehalten und nur fehlende ergaenzen. Team 1 fasst bei der Django-Umstellung ohnehin jede Datei an - Docstrings dabei gleich mitzumachen ist effizient.

### 3.1 Bestandsaufnahme
- [x] Alle Funktionen ohne Docstring identifizieren (AST-Audit ueber alle Module)
- [x] Liste der fehlenden Docstrings erstellen
  <!-- Ergebnis: fast alles war bereits dokumentiert. Fehlend nur `Submission.__str__` (ergaenzt) und die inneren Django `class Meta` (bleiben bewusst ohne Docstring, Absprache mit Emil). Zusatz: `parser.parse_all_quarters` hatte einen Args-/Returns-Block - auf den natuerlichen Stil (3.3) umgeschrieben. -->


### 3.2 Docstrings schreiben
- [x] `config.py` - Modul-Docstring pruefen/ergaenzen
- [x] `main.py` - alle Funktionen pruefen (`parse_args`, `setup_logging`, `main`, ...)
  <!-- Hinweis: das im Plan genannte `run_pipeline` existiert nicht; vorhandene Funktionen sind parse_args, preflight_checks, print_summary, main, setup_logging, setup_directories - alle haben Docstrings. -->
- [x] `modules/__init__.py` - Modul-Docstring (Re-Export von get_engine in 2.6 entfernt)
- [x] `modules/downloader.py` - alle Funktionen pruefen
- [x] `modules/parser.py` - alle Funktionen pruefen
- [x] `modules/data_preparation.py` - alle Funktionen pruefen (z.B. `_clean_columns`, `_parse_date`)
- [x] `modules/db_manager.py` - alle Funktionen pruefen
- [x] `modules/validation.py` - alle Funktionen pruefen
- [x] `modules/evaluation.py` - alle Funktionen pruefen (z.B. `_format_value`, `_add_logo`, `_setup_chart_style`)
- [x] `pipeline/models.py` - Models + `__str__` (in Aufgabe 2 erstellt, hier mitgeprueft)

### 3.3 Stil-Regeln fuer Docstrings
- Natuerlicher, erklaerungsreicher Stil (kein Schema-Docstring)
- Englisch
- Erklaert **warum**, nicht nur **was**
- Beispiel aus dem bestehenden Code:
  ```python
  def read_tsv(filepath):
      """Read a TSV into a DataFrame.

      Falls back to latin-1 if UTF-8 chokes. ACCESSION_NUMBER is
      forced to string - otherwise pandas might mangle it.
      """
  ```
- Keine `Args:` / `Returns:` Bloecke - stattdessen natuerlich im Text erwaehnen
- [x] Unter `/docs` dokumentieren: `docstring_guidelines.md`

---

## Aufgabe 4: Hardcoded-Werte flexibel machen (Team 2 - Kenan & Matthias)

Alle hartcodierten Werte sollen ueber `config.py` oder `.env` konfigurierbar sein. Team 2 uebernimmt diese Aufgabe zusammen mit der Historie-Erweiterung (Aufgabe 5), damit alle config-Aenderungen in einer Hand liegen und keine Merge-Konflikte entstehen.

### 4.1 Identifizierte Hardcoded-Stellen

- [x] `config.py` - `USER_AGENT` String → in `.env` auslagern
- [x] `config.py` - `SCHEMA_NAME = "group01"` → entfaellt durch Django-Umstellung (Team 1)
- [x] `config.py` - `TARGET_YEAR = 2025` → in Aufgabe 5 erledigt (START_YEAR/END_YEAR)
- [x] `config.py` - `REQUEST_DELAY = 0.2` → in `.env` auslagern
- [x] `config.py` - `CREATED_BY = "group01"` → in `.env` auslagern
- [x] `evaluation.py` - Farbwerte (`COLOR_PURCHASE`, etc.) → `config.CHART_COLORS` Dictionary
- [x] `evaluation.py` - `LOGO_PATH` → `config.LOGO_PATH`
- [x] `evaluation.py` - `MONTH_NAMES` Dictionary → `config.MONTH_NAMES` (dict beibehalten, calendar-Modul bringt keinen Mehrwert)
- [x] `db_manager.py` - `innodb_lock_wait_timeout` → entfaellt durch Django/PostgreSQL-Umstellung (Team 1)
- [x] `validation.py` - `KNOWN_TRANS_CODES` Set → `config.KNOWN_TRANS_CODES`
- [x] `validation.py` - `MAX_REASONABLE_PRICE` → `config.MAX_REASONABLE_PRICE`
- [x] `downloader.py` - `max_retries=3` Default → `config.MAX_RETRIES`

### 4.2 Umsetzung
- [x] Alle identifizierten Werte nach `config.py` oder `.env` verschoben
- [x] `.env.example` aktualisiert mit allen neuen Variablen
- [x] Bestehende Funktionalitaet unveraendert
- [x] Unter `/docs` dokumentieren: `configuration.md`

---

## Aufgabe 5: Historie erweitern - 2020 bis 2025 (Team 2 - Kenan & Matthias)

Statt nur 2025 sollen die Jahre 2020 bis 2025 abgedeckt werden.

### 5.1 config.py anpassen
- [x] `TARGET_YEAR = 2025` ersetzen durch `TARGET_YEARS = range(2020, 2026)` (oder Liste)
- [x] Alternativ: `START_YEAR` und `END_YEAR` in `.env`

### 5.2 downloader.py anpassen
- [x] `get_available_quarters()` muss fuer mehrere Jahre scrapen
- [x] Download-Logik muss ueber alle Jahre iterieren
- [x] Bereits heruntergeladene Dateien ueberspringen (existiert schon)

### 5.3 parser.py anpassen
- [x] ZIP-Extraktion muss mit mehreren Jahren umgehen
- [x] Ordnerstruktur: `data/extracted/2020Q1/`, `data/extracted/2021Q2/`, etc.

### 5.4 data_preparation.py anpassen
- [x] `prepare_all_data()` muss alle Jahre verarbeiten
- [x] Keine Aenderungen an der Transformationslogik noetig

### 5.5 db_manager.py anpassen
- [x] Import muss fuer alle Quartale funktionieren
- [x] Idempotenz pro Quartal bleibt bestehen
- [x] Pipeline-Log wird weiterhin nie geloescht

### 5.6 evaluation.py anpassen
- [x] Charts und Tabellen fuer jedes Jahr einzeln generieren
- [x] Oder: jahresuebergreifende Auswertungen ermoelichen
- [x] `MONTH_NAMES` und Ordnerstruktur muessen mehrjaehrig funktionieren
- [x] PDF-Report: entweder pro Jahr oder als Gesamtreport
- [x] Ueberblick-Charts (Trend, Sentiment, Heatmap) pro Jahr

### 5.7 main.py anpassen
- [x] CLI-Parameter: `--years 2020-2025` oder `--year 2023`
- [x] Default: alle konfigurierten Jahre

### 5.8 Testen
<!-- Verifiziert 04.06.2026 durch den kompletten Lauf auf dem SQLite-Fallback. -->
- [x] Download fuer 2020 bis 2025 funktioniert - 24 Quartals-ZIPs (~200 MB) geladen
- [x] Datenimport fuer alle Jahre laeuft fehlerfrei - 4.612.977 Zeilen, 0 Fehler
- [x] Validierung funktioniert ueber alle Jahre - nonderiv 100,0 %, deriv 99,9 % gueltig
- [x] Evaluation generiert korrekte Charts pro Jahr - 450 Charts + 6 Jahres-PDFs
- [x] Unter `/docs` dokumentieren: `multi_year_extension.md`

---

## Aufgabe 6: Code Review und Bugsuche (Alle)

Systematische Ueberpruefung des gesamten Codes nach Abschluss aller anderen Aufgaben.

### 6.1 Funktionale Pruefung
- [x] Pipeline komplett durchlaufen lassen (Download → Evaluation) - voller Lauf 2020-2025 auf SQLite
- [ ] Ergebnisse stichprobenartig mit SEC-Rohdaten vergleichen - offen (manuelle Teamaufgabe)
- [x] Idempotenz testen: Pipeline zweimal ausfuehren, gleiche Ergebnisse? - Unit-Test deckt Re-Import ab (gleiche Zeilenzahl), Lauf zeigt Delete-then-Insert
- [x] Edge Cases: leere Quartale, fehlende Dateien, Netzwerkfehler - durch Unit-Tests abgedeckt (parser/downloader) + Leer-DataFrame-Bug gefixt

### 6.2 Code-Qualitaet
- [x] Alle Funktionen haben Docstrings - AST-Audit sauber (Gerüst-Dateien `apps/admin/views/__init__` ergaenzt)
- [x] Keine hartcodierten Werte mehr (ausser wo bewusst entschieden) - in Aufgabe 4 nach `config.py`/`.env` ausgelagert
- [x] Keine ungenutzten Imports oder Variablen - `admin.py`/`views.py` bereinigt
  <!-- Ausnahme: `seaborn` in evaluation.py hat ein `# noqa: F401` (bewusst behalten).
       Nicht eigenmaechtig entfernt - Team sollte entscheiden, ob es weg kann. -->
- [x] Einheitlicher Code-Stil ueber alle Module - PEP-8, py_compile sauber, pyflakes clean
- [x] Keine KI-Footprints im Code - grep ueber alle `.py` sauber

### 6.3 Sicherheit
- [x] Keine Credentials im Code oder auf GitHub - grep sauber
- [x] `.env` ist in `.gitignore` - mit `git check-ignore` bestaetigt
- [x] SQL-Injection durch Django ORM verhindert - kein Raw-SQL/`.raw()`/`cursor.execute` im Code
- [x] Keine sensiblen Daten in Logs - Logs enthalten nur Quartale/Zeilenzahlen/URLs, keine Zugangsdaten

### 6.4 Performance
<!-- Beobachtungen aus dem Lauf 04.06.2026 (SQLite): Import 13-20 s/Quartal,
     Gesamt ~21 min fuer 4,6 Mio. Zeilen. Rigoroses Profiling steht noch aus. -->
- [ ] Langsame Queries identifizieren - offen (kein Profiling durchgefuehrt)
- [x] Batch-Groessen pruefen - `BATCH_SIZE=5000` hat 4,6 Mio. Zeilen problemlos verarbeitet
- [x] Unnoetige DB-Roundtrips eliminieren - durchgaengig `bulk_create`/`bulk_update`/`values().annotate()`
- [ ] Speicherverbrauch bei grossen Datenmengen pruefen - offen (kein Memory-Profiling)

### 6.5 Dokumentation
- [x] README.md ist aktuell und vollstaendig - Setup-Hinweis + Test-Abschnitt ergaenzt
- [x] Alle `/docs` Dateien sind vorhanden und verstaendlich - inkl. `sqlite_fallback_und_tests.md`
- [x] `CLAUDE.md` ist aktuell - keine Aenderung noetig
- [ ] Diese `Plan.md` ist vollstaendig abgehakt - es bleiben bewusst offene Punkte (PostgreSQL-Zugang, SEC-Stichprobe, Profiling)

### 6.6 Lokaler SQLite-Fallback und Unit-Tests
<!-- Ergaenzt nach Absprache mit Umeyr: lokaler Test ohne PostgreSQL-Server
     war blockiert, solange die Zugangsdaten fehlen. Loesung nutzt das
     Django ORM, das die Datenbank austauschbar macht. -->

- [x] SQLite-Fallback in `settings.py`: bei `DB_ENGINE=...sqlite3` wird eine
  lokale Datei statt PostgreSQL genutzt (PostgreSQL bleibt der Standard)
- [x] `*.sqlite3` in `.gitignore` - die DB-Datei landet nie auf GitHub
- [x] `.env.example`: SQLite-Umschaltung dokumentiert (auskommentiert)
- [x] Verifiziert: `migrate` baut auf SQLite alle 7 Tabellen identisch auf
- [x] Unit-Tests unter `pipeline/tests/` (Djangos eingebautes Test-Framework,
  kein neues Paket): data_preparation, validation (alle 8 Checks), parser,
  downloader (Netzwerk gemockt), db_manager (Idempotenz + Orphan-Drop), models
- [x] Tests laufen gegen eine temporaere SQLite-Test-DB: `python manage.py test`
  (30 Tests, gruen, ohne PostgreSQL-Zugang)
- [x] Unter `/docs` dokumentieren: `sqlite_fallback_und_tests.md`
- [x] Gefundener Edge-Case gefixt: `prepare_transactions`/`prepare_holdings`
  pruefen jetzt zuerst auf leer, dann erst `_clean_columns` - eine voellig
  spaltenlose leere DataFrame (wie `read_tsv` sie bei fehlender Datei liefert)
  crasht nicht mehr. Regressionstest ergaenzt.

---

## Quellen

Diese Quellen werden im Projekt verwendet. Keine anderen ohne Absprache:

- **SEC EDGAR Insider Transactions:** `https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets`
- **SEC Form 4 Dokumentation:** Die `FORM_345_readme.htm` und `FORM_345_metadata.json` aus den ZIP-Archiven
- **Python-Pakete:** Nur die in `requirements.txt` gelisteten

---

## Aenderungsprotokoll

| Datum | Aenderung | Begruendung |
|-------|-----------|-------------|
| 30.05.2026 | Aufgaben 3 und 4 getauscht: Docstrings → Team 1, Hardcoded → Team 2 | Vermeidung von Merge-Konflikten bei config.py (TARGET_YEAR wird von Team 2 in Aufgabe 5 umgebaut) |
| 30.05.2026 | Abschnitt 2.8 (PostgreSQL-Zugangsdaten) ergaenzt | PostgreSQL-Zugangsdaten liegen noch nicht vor; bis dahin Arbeit mit Platzhaltern in `.env` (Absprache mit Emil) |
| 04.06.2026 | Abschnitt 6.6 (SQLite-Fallback + Unit-Tests) ergaenzt | Lokales Testen war blockiert, solange der PostgreSQL-Server fehlt; das Django ORM macht SQLite zu einem Ein-Zeilen-Fallback (Absprache mit Umeyr) |
| 04.06.2026 | Kompletter Lauf 2020-2025 auf SQLite + Code-Review (Aufgabe 6) | 4,6 Mio. Zeilen, 0 Fehler; Preflight SQLite-tauglich gemacht, Leer-DataFrame-Bug gefixt, Gerüst-Dateien aufgeraeumt. Offen bleiben: PostgreSQL-Zugang, SEC-Stichprobe, Profiling (Absprache mit Umeyr) |
| 04.06.2026 | Output-Struktur pro Jahr + Repo-Cleanup | `output/<Jahr>/charts|tables|report` statt flach gemischt (config.py-Helfer + evaluation.py umgebaut, neu generiert: 6 PDFs/450 Charts/432 CSVs). Cleanup: leere emoji-`team.md` (2x) und Root-`__init__.py` entfernt, `setub_project.md`/`how_to_claude.md` nach `notes/` (Absprache mit Umeyr) |
