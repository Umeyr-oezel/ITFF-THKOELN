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
- [ ] Pipeline einmal lokal testen (`python main.py --skip-download`)
  - Blockiert bis PostgreSQL-Zugangsdaten vorliegen (Preflight-Check braucht erreichbare DB)
  - Fix: `modules/__init__.py` war leer, exportiert jetzt wieder `get_engine` (Imports laufen, CLI laeuft)

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
- [ ] Migrations ausfuehren (`migrate`) - blockiert bis PostgreSQL-Zugang da ist

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
- [ ] Migrations laufen fehlerfrei durch (`migrate`) - blockiert bis DB-Zugang
- [ ] Pipeline laeuft komplett mit PostgreSQL - blockiert bis DB-Zugang
- [ ] Datenimport funktioniert idempotent - blockiert bis DB-Zugang
- [ ] Validierung liefert gleiche Ergebnisse wie vorher - blockiert bis DB-Zugang
- [ ] Evaluation/Charts werden korrekt generiert - blockiert bis DB-Zugang
- [x] Unter `/docs` dokumentieren: `django_migration.md`

### 2.8 PostgreSQL-Zugangsdaten
Stand: Die PostgreSQL-Zugangsdaten liegen **noch nicht vor**. Bis dahin wird
ueberall mit Platzhaltern gearbeitet, damit die Umstellung trotzdem vorbereitet
werden kann.

- [x] In `.env` Platzhalter fuer die DB-Zugangsdaten eintragen (`PLATZHALTER_*`)
- [ ] Echte PostgreSQL-Zugangsdaten in `.env` eintragen, sobald sie vorliegen
- [ ] `.env.example` auf PostgreSQL-Felder umstellen (`DB_ENGINE`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`)
- [ ] Pruefen, dass keine echten Zugangsdaten im Code oder auf GitHub landen (nur ueber `.env`)

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

- [ ] `config.py:12` - `USER_AGENT` String → in `.env` auslagern
- [ ] `config.py:22` - `SCHEMA_NAME = "group01"` → in `.env` auslagern (wird nach Django-Umstellung evtl. obsolet)
- [ ] `config.py:34` - `TARGET_YEAR = 2025` → wird in Aufgabe 5 zu `TARGET_YEARS` umgebaut
- [ ] `config.py:36` - `REQUEST_DELAY = 0.2` → in `.env` auslagern
- [ ] `config.py:37` - `CREATED_BY = "group01"` → in `.env` auslagern
- [ ] `evaluation.py:46-51` - Farbwerte (`COLOR_PURCHASE`, etc.) → in `config.py` als Dictionary
- [ ] `evaluation.py:54-55` - `LOGO_PATH` → in `config.py`
- [ ] `evaluation.py:191` - `MONTH_NAMES` Dictionary → pruefen ob `calendar` Modul besser waere
- [ ] `db_manager.py:195` - `"SET innodb_lock_wait_timeout = 120"` → in `config.py` (entfaellt bei PostgreSQL)
- [ ] `validation.py:14-17` - `KNOWN_TRANS_CODES` Set → in `config.py`
- [ ] `validation.py:19` - `MAX_REASONABLE_PRICE = 1_000_000` → in `config.py`
- [ ] `downloader.py:46` - `max_retries=3` Default → in `config.py`

### 4.2 Umsetzung
- [ ] Alle identifizierten Werte nach `config.py` oder `.env` verschieben
- [ ] `.env.example` aktualisieren mit allen neuen Variablen
- [ ] Bestehende Funktionalitaet darf sich nicht aendern
- [ ] Unter `/docs` dokumentieren: `configuration.md`

---

## Aufgabe 5: Historie erweitern - 2020 bis 2025 (Team 2 - Kenan & Matthias)

Statt nur 2025 sollen die Jahre 2020 bis 2025 abgedeckt werden.

### 5.1 config.py anpassen
- [ ] `TARGET_YEAR = 2025` ersetzen durch `TARGET_YEARS = range(2020, 2026)` (oder Liste)
- [ ] Alternativ: `START_YEAR` und `END_YEAR` in `.env`

### 5.2 downloader.py anpassen
- [ ] `get_available_quarters()` muss fuer mehrere Jahre scrapen
- [ ] Download-Logik muss ueber alle Jahre iterieren
- [ ] Bereits heruntergeladene Dateien ueberspringen (existiert schon)

### 5.3 parser.py anpassen
- [ ] ZIP-Extraktion muss mit mehreren Jahren umgehen
- [ ] Ordnerstruktur: `data/extracted/2020Q1/`, `data/extracted/2021Q2/`, etc.

### 5.4 data_preparation.py anpassen
- [ ] `prepare_all_data()` muss alle Jahre verarbeiten
- [ ] Keine Aenderungen an der Transformationslogik noetig

### 5.5 db_manager.py anpassen
- [ ] Import muss fuer alle Quartale funktionieren
- [ ] Idempotenz pro Quartal bleibt bestehen
- [ ] Pipeline-Log wird weiterhin nie geloescht

### 5.6 evaluation.py anpassen
- [ ] Charts und Tabellen fuer jedes Jahr einzeln generieren
- [ ] Oder: jahresuebergreifende Auswertungen ermoelichen
- [ ] `MONTH_NAMES` und Ordnerstruktur muessen mehrjaehrig funktionieren
- [ ] PDF-Report: entweder pro Jahr oder als Gesamtreport
- [ ] Ueberblick-Charts (Trend, Sentiment, Heatmap) pro Jahr

### 5.7 main.py anpassen
- [ ] CLI-Parameter: `--years 2020-2025` oder `--year 2023`
- [ ] Default: alle konfigurierten Jahre

### 5.8 Testen
- [ ] Download fuer 2020 bis 2025 funktioniert
- [ ] Datenimport fuer alle Jahre laeuft fehlerfrei
- [ ] Validierung funktioniert ueber alle Jahre
- [ ] Evaluation generiert korrekte Charts pro Jahr
- [ ] Unter `/docs` dokumentieren: `multi_year_extension.md`

---

## Aufgabe 6: Code Review und Bugsuche (Alle)

Systematische Ueberpruefung des gesamten Codes nach Abschluss aller anderen Aufgaben.

### 6.1 Funktionale Pruefung
- [ ] Pipeline komplett durchlaufen lassen (Download → Evaluation)
- [ ] Ergebnisse stichprobenartig mit SEC-Rohdaten vergleichen
- [ ] Idempotenz testen: Pipeline zweimal ausfuehren, gleiche Ergebnisse?
- [ ] Edge Cases: leere Quartale, fehlende Dateien, Netzwerkfehler

### 6.2 Code-Qualitaet
- [ ] Alle Funktionen haben Docstrings
- [ ] Keine hartcodierten Werte mehr (ausser wo bewusst entschieden)
- [ ] Keine ungenutzten Imports oder Variablen
- [ ] Einheitlicher Code-Stil ueber alle Module
- [ ] Keine KI-Footprints im Code

### 6.3 Sicherheit
- [ ] Keine Credentials im Code oder auf GitHub
- [ ] `.env` ist in `.gitignore`
- [ ] SQL-Injection durch Django ORM verhindert
- [ ] Keine sensiblen Daten in Logs

### 6.4 Performance
- [ ] Langsame Queries identifizieren
- [ ] Batch-Groessen pruefen
- [ ] Unnoetige DB-Roundtrips eliminieren
- [ ] Speicherverbrauch bei grossen Datenmengen pruefen

### 6.5 Dokumentation
- [ ] README.md ist aktuell und vollstaendig
- [ ] Alle `/docs` Dateien sind vorhanden und verstaendlich
- [ ] `CLAUDE.md` ist aktuell
- [ ] Diese `Plan.md` ist vollstaendig abgehakt

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
