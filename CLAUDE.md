# CLAUDE.md - Verbindliche Projektregeln

## Workflow-Ablauf (STRIKT EINHALTEN)

### Vor jeder Nachricht
1. Diese Datei (`CLAUDE.md`) vollstaendig lesen
2. `Plan.md` vollstaendig lesen und den aktuellen Stand pruefen
3. Erst dann mit der Arbeit beginnen

### Waehrend der Arbeit
- Aufgabe bearbeiten bis sie **vollstaendig** erledigt ist
- Keine Teilaufgaben einzeln committen - nur ganze Aufgaben
- Nach Abschluss einer Aufgabe: dokumentieren, betroffene Dateien auf GitHub aktualisieren
- Dann fragen: "Machen wir weiter?"

### Session beenden
- Nutzer sagt er hoert auf
- Claude dokumentiert den aktuellen Stand
- Claude aktualisiert betroffene Dateien auf GitHub
- Session ist beendet

## GitHub-Regeln

### Was wird aktualisiert
- **NUR betroffene/neue Dateien** - niemals das ganze Repository neu pushen
- Commits nur nach Abschluss einer **ganzen Aufgabe** (keine Teilaufgaben)
- Commit-Messages auf Deutsch, klar und beschreibend

### Branches
- `main` ist der Hauptbranch
- Fuer grosse Features: eigenen Branch erstellen, nach Abschluss mergen

## Plan.md - Pflege (PFLICHT)

### Checkboxen
- `- [ ]` wird zu `- [x]` sobald eine Aufgabe erledigt ist
- Checkboxen werden nach JEDER erledigten Aufgabe sofort aktualisiert

### Aenderungen an Aufgaben
- Geaenderte Teilaufgaben werden ~~durchgestrichen~~
- Direkt darunter als Kommentar die Aenderung dokumentieren
- Beispiel:
  ```
  ~~- [x] Daten als CSV exportieren~~
  <!-- Geaendert: Export erfolgt als TSV statt CSV, weil SEC-Daten Tab-separiert sind -->
  - [x] Daten als TSV exportieren
  ```

### Aenderungen und Abweichungen
- Aenderungen am Plan **nur nach Absprache mit dem Nutzer**
- Abweichungen vom Plan **nur nach Absprache mit dem Nutzer**
- Niemals eigenmaechtigt Aufgaben aendern, hinzufuegen oder entfernen

## Code-Stil (EXAKT BEIBEHALTEN)

### Sprache
- Code, Variablennamen, Docstrings, Kommentare: **Englisch**
- Dokumentation (Plan.md, docs/): **Deutsch**

### Formatierung
- PEP-8
- 4 Spaces Einrueckung
- Imports: Standardbibliothek, dann Drittanbieter, dann eigene Module (jeweils alphabetisch)
- Leerzeile zwischen Import-Gruppen

### Docstrings (PFLICHT - IMMER)
- Jedes Modul hat einen Modul-Docstring am Anfang
- Jede Funktion hat einen Docstring
- Stil: natuerlich, erklaerend, nicht formelhaft
- Beispiel aus dem Projekt:
  ```python
  def read_tsv(filepath):
      """Read a TSV into a DataFrame.

      Falls back to latin-1 if UTF-8 chokes. ACCESSION_NUMBER is
      forced to string - otherwise pandas might mangle it.
      """
  ```

### Variablen und Konstanten
- Konstanten: `UPPER_SNAKE_CASE` (z.B. `SEC_BASE_URL`, `BATCH_SIZE`)
- Funktionen: `lower_snake_case` (z.B. `get_available_quarters`)
- Klassen: `PascalCase`
- Logger: `logger = logging.getLogger(__name__)` pro Modul

### Keine KI-Footprints
- Kein `# AI generated`, kein `# Created by Claude`, keine kuenstlichen Marker
- Code soll natuerlich wirken, als haette ein Mensch ihn geschrieben
- Keine uebermaessig ausfuehrlichen Kommentare die offensichtliches erklaeren
- Keine uebertrieben defensive Programmierung

### Fehlerbehandlung
- Logging statt print-Statements
- `logger.info()` fuer normale Ablaeufe
- `logger.warning()` fuer unerwartete aber handhabbare Situationen
- `logger.error()` fuer Fehler
- Exceptions nur wo noetig, nicht ueberall try/except

## Projektstruktur

```
ITFF-THKOELN/
├── CLAUDE.md              # Diese Datei
├── Plan.md                # Verbindlicher Projektplan
├── README.md              # Wird staendig aktualisiert
├── requirements.txt       # Python-Abhaengigkeiten
├── .env.example           # Template fuer Credentials
├── .gitignore             # .env, data/, __pycache__, venv/, .idea/
├── config.py              # Zentrale Konfiguration
├── main.py                # Pipeline-Einstiegspunkt
├── modules/
│   ├── __init__.py
│   ├── downloader.py      # SEC-Daten herunterladen
│   ├── parser.py          # ZIP entpacken, TSV/JSON lesen
│   ├── data_preparation.py # Daten aufbereiten
│   ├── db_manager.py      # MySQL-Datenbankoperationen
│   ├── validation.py      # Datenvalidierung
│   └── evaluation.py      # Auswertung und Charts
├── docs/                  # Dokumentation jeder grossen Aufgabe
├── data/                  # Rohdaten und extrahierte Daten (in .gitignore)
├── output/                # Charts, Tabellen, Reports
├── assets/                # Logos, Bilder
└── Documents/             # PDFs (Dokumentation, Berichte)
```

## Datenquellen (NUR DIESE VERWENDEN)

- **SEC EDGAR:** `https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets`
- **User-Agent:** Bei jedem SEC-Request den konfigurierten User-Agent senden
- Keine anderen Datenquellen ohne Absprache

## Technische Regeln

- `ACCESSION_NUMBER` immer als `str` behandeln (dtype in pandas setzen)
- Dynamische Quartalserkennung - kein Hardcoding von Q1-Q4
- DB-Credentials ausschliesslich ueber `.env`
- Idempotente Pipeline: Delete-then-Insert (pipeline_log wird nie geloescht)
- `REQUEST_DELAY = 0.2` bei SEC-Anfragen einhalten
- MySQL-Schema: `group01`

## Abhaengigkeiten (requirements.txt)

Nur diese Pakete verwenden. Neue Pakete nur nach Absprache:
- pandas, requests, beautifulsoup4, sqlalchemy, pymysql
- matplotlib, seaborn, numpy, fpdf2, python-dotenv

## Dokumentation

### README.md
- Wird nach jeder abgeschlossenen Aufgabe aktualisiert
- Enthaelt: Projektbeschreibung, Setup-Anleitung, Nutzung, aktueller Stand

### /docs Ordner
- Jede grosse Aufgabe wird nutzerfreundlich dokumentiert
- Dokumentation auf Deutsch
- Verstaendlich fuer Projektmitglieder die nicht am Code beteiligt waren

## Ideen und Verbesserungen

- Claude darf Ideen und Verbesserungsvorschlaege einbringen
- Diese werden **IMMER zuerst besprochen** bevor sie umgesetzt werden
- Niemals eigenmaechtigt "Verbesserungen" implementieren

## Skills und Agents

- **Skills:** Nur verwenden wenn der Nutzer explizit danach fragt
- **Agents:** Immer nutzen wenn es die effizienteste Loesung ist
