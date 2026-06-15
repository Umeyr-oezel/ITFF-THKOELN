# Code-Review (Aufgabe 2) – Befunde und Fixes

Dieses Dokument hält das datei-für-datei-Review aus Aufgabe 2 fest. Für
jede Datei steht hier, was geprüft wurde (Effizienz, Hardcoded-Werte,
Bugs), was geändert wurde und warum. Geprüft wird von Team 2 (Kenan,
Matthias).

**Stand:** Code-Review vollständig abgeschlossen (2.2 bis 2.6).

Die Tests laufen nach allen Änderungen vollständig grün durch (31 Tests).
Lokal ausführen mit dem SQLite-Fallback:

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=test_local.sqlite3 python manage.py test
```

---

## Abgestimmte Entscheidungen

Vier Punkte brauchten laut CLAUDE.md eine Absprache. Festgelegt wurde:

- **A – Jahres-PDF-Statistik:** Die Statistik-Seite jedes PDF-Reports wird
  auf das jeweilige Jahr eingeschränkt (vorher: pipeline-weite Summen über
  alle Jahre in jedem Jahresreport). → umgesetzt.
- **B – Hardcoded auslagern:** `BATCH_SIZE` und `TOP_N` wandern nach
  `config.py` und werden über `.env` überschreibbar. → umgesetzt.
- **C – Query-Refactor in `evaluation.py`:** Wird jetzt umgesetzt (statt auf
  Aufgabe 4 zu schieben), weil es laut Aufgabe 2.1 ausdrücklich um
  „unnötige DB-Roundtrips" geht. → umgesetzt, mit Output-Kontrolle (siehe
  unten).
- **D – Toter Orphan-Check in `validation.py`:** **Bleibt erhalten.** Bei
  genauer Prüfung ist er kein echter toter Code: Die Funktion
  `_check_orphan_records` ist durch einen Unit-Test abgedeckt und als
  dokumentiertes Sicherheitsnetz hinter dem echten Foreign Key gewollt. Er
  löst in der Praxis nur deshalb nie aus, weil der FK die Integrität
  garantiert. Löschen würde den Test entfernen und die dokumentierten
  „8 Checks" auf 7 reduzieren – daher bewusst behalten.

---

## 2.2 Root-Dateien

### `config.py`
- **Hardcoded (behoben):** `BATCH_SIZE` war als einziger Pipeline-Wert fest
  verdrahtet, während alle Nachbarwerte über `os.getenv(...)` aus `.env`
  kommen. Jetzt: `BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5000))`.
- **Neu:** `TOP_N = int(os.getenv("TOP_N", 5))` – die Tiefe der monatlichen
  Ranglisten (Top-N / Bottom-N) war vorher als `5` und „Top 5"/„Bottom 5"
  über `evaluation.py` verstreut. Beide neuen Schalter stehen auch in
  `.env.example`.
- Sonst: sauber strukturiert, keine Bugs.

### `main.py`
- **Bug (behoben):** `resolve_years` stürzte bei ungültiger `--years`-Eingabe
  (z. B. `2020-2021-2022` oder Text) mit einem rohen `ValueError` ab. Jetzt
  gibt es eine klare Fehlermeldung mit Beispiel und sauberem Abbruch. Werden
  `--year` und `--years` zusammen angegeben, weist eine Warnung darauf hin,
  dass `--year` Vorrang hat.
- **Effizienz (behoben):** `print_summary` lief zweimal mit `os.walk` über
  `output/` (einmal für PNG, einmal für CSV). Jetzt zählt ein einziger
  Durchlauf beide Dateitypen.

### `manage.py`
- Unveränderte Django-Boilerplate. Geprüft, nichts zu tun.

---

## 2.3 modules/

### `modules/__init__.py`
- Nur Modul-Docstring. Geprüft, nichts zu tun.

### `modules/downloader.py`
- Sauber und robust (Retry mit Backoff, Streaming-Download, Skip
  vorhandener Dateien). Keine Bugs.
- **Notiert, nicht geändert (optional, DRY):** Der Aufbau des
  Jahres-Regex (`<jahr>q<n>_form345.zip`) steht in `get_available_quarters`
  und `list_existing_quarters` doppelt. Könnte später in einen kleinen
  Helper – bewusst zurückgestellt, um den Scope dieses Durchgangs eng zu
  halten.

### `modules/parser.py`
- Solide (Encoding-Fallback latin-1, leere/fehlende Dateien werden sauber
  abgefangen). Keine Befunde.

### `modules/data_preparation.py`
- **Toter Code (behoben):** `add_metadata` setzte
  `df["created_at"] = datetime.now()`, aber dieser Wert wurde nie in die DB
  geschrieben – die Modelle füllen `created_at` selbst über `auto_now_add`.
  Die Zeile und der dadurch ungenutzte `datetime`-Import sind entfernt; der
  Docstring erklärt jetzt, dass die DB den Zeitstempel setzt.

### `modules/db_manager.py`
- Robust: Delete-then-Insert je Quartal in **einer** atomaren Transaktion,
  Orphan-Zeilen werden vor dem Insert verworfen und geloggt, `pipeline_log`
  bleibt als Audit-Trail erhalten. Keine Bugs.
- **Notiert, nicht geändert:** Bei Erfolg zählt `log_pipeline_run` nur die
  Submissions als `records_imported` (Kind-Tabellen nicht mit). Leicht
  irreführend, aber als Sammeleintrag (`"all"`) dokumentiert – bewusst
  belassen.

### `modules/validation.py`
- Logik der 8 Checks korrekt, vektorisierte Auswertung. Keine Bugs.
- **Orphan-Check:** siehe Entscheidung **D** oben – bewusst als getestetes
  Sicherheitsnetz behalten.
- **Notiert (Performance, gehört zu Aufgabe 4.3):** `_validate_table` lädt die
  komplette Tabelle (bei 4,6 Mio. Zeilen) in einen DataFrame. Speicher- und
  Laufzeitthema, das sinnvoll gegen den echten PostgreSQL-Server profiliert
  wird – daher hier nur notiert, nicht geändert.

### `modules/evaluation.py`
- **Bug (behoben, Semantik):** Die Statistik-Seite jedes Jahres-PDFs zeigte
  globale Zahlen über **alle** Jahre/Quartale. Der „Annual Report 2020"
  listete damit u. a. Quartale 2021–2025. `_get_pipeline_stats(year)` ist
  jetzt über `source_quarter` aufs Jahr eingeschränkt (Entscheidung A).
- **Bug (behoben, Robustheit):** In `create_bar_chart` führte ein
  Maximalwert von `0` (z. B. Volumen ganz ohne Preise) zu einer
  entarteten Achse (`set_xlim(0, 0)`). Ein Guard (`max_val = max_val or 1`)
  fängt das ab.
- **Effizienz (behoben, Entscheidung C):** Pro Monat liefen **6** separate
  GROUP-BY-Aggregations-Queries, obwohl sich die drei Purchase- bzw. die
  drei Sale-Ranglisten nur in Sortierung/Limit unterscheiden. Neu:
  - `query_month_aggregates(trans_code, month, year)` macht **eine**
    Aggregation je `(trans_code, Monat)` und liefert alle Issuer.
  - `top_n_by(df, order_col)` schneidet die Top-N je Metrik in pandas.
  - `query_monthly_ranking(...)` bleibt als dünner Wrapper erhalten (für die
    Heatmap und Bestandstests).

  Damit sinkt die Zahl der schweren Aggregations-Queries im Monats-Loop von
  6 auf 2 pro Monat.
- **Toter Import (behoben):** `import seaborn as sns` wurde nie benutzt und
  ist entfernt.
- **Hardcoded (behoben):** `TOP_N` (vorher `[:5]` und „Top 5"/„Bottom 5"
  bzw. „Top-5" in Titeln/Heatmap) kommt jetzt aus `config.py`.

#### Hinweis zur Output-Gleichheit nach dem C-Refactor
Der Refactor soll die erzeugten Charts/CSVs **nicht** verändern. `top_n_by`
repliziert die alte `ORDER BY ... LIMIT`-Semantik bewusst: NULL-Aggregate
landen hinten (`na_position="last"`), und ein stabiler Sort (`mergesort`)
hält Gleichstände in ihrer Abrufreihenfolge. Die Test-Suite bleibt grün.

Eine **visuelle Vorher-/Nachher-Kontrolle gegen echte Daten** steht noch
aus, weil lokal keine befüllte Datenbank vorliegt. Sie sollte beim ersten
Lauf gegen eine Datenbank mit Daten (SQLite-Fallback oder PostgreSQL)
nachgeholt werden.

---

## 2.4 Django (pipeline/ + secpipeline/)

### `pipeline/models.py`
- Sieben Modelle spiegeln die früheren Raw-SQL-Tabellen sauber als Django-
  ORM-Klassen. Alle Docstrings vorhanden, Indizes korrekt, `CASCADE`-Delete
  funktioniert (Unit-Test in `test_models.py` beweist das).
- `ValidationLog` verwendet absichtlich keinen ForeignKey auf `Submission`
  (im Docstring erklärt: ein Check kann auch Orphan-Records flaggen, deren
  Submission noch nicht existiert).
- Keine Befunde, keine Änderungen.

### `pipeline/admin.py`
- Nur Modul-Docstring. `django.contrib.admin` nicht in `INSTALLED_APPS` –
  korrekt dokumentiert, nichts zu registrieren. Keine Änderungen.

### `pipeline/apps.py`
- Standard-AppConfig, korrekt. Keine Änderungen.

### `pipeline/views.py`
- Nur Modul-Docstring. Kein Web-Layer – korrekt, keine Änderungen.

### `secpipeline/settings.py`
- **Hardcoded (behoben):** `SECRET_KEY` war als Literal-String direkt im
  Code. Jetzt: `os.getenv('DJANGO_SECRET_KEY', '<insecure-default>')` –
  der Default reicht für lokale Entwicklung; für Produktion wird ein echter
  Schlüssel in `.env` gesetzt. Eintrag auch in `.env.example` ergänzt.
- **Hardcoded (behoben):** `DEBUG = True` war fest verdrahtet. Jetzt:
  `os.getenv('DJANGO_DEBUG', 'True') == 'True'` – für Produktion oder CI
  kann der Wert in `.env` auf `False` gesetzt werden.
- **Boilerplate (behoben):** Der auto-generierte Django-Startproject-
  Kommentarblock (mit Docs-URLs und „Generated by"-Zeile) wurde durch einen
  präzisen Modul-Docstring ersetzt.
- Datenbank-Logik (SQLite-Fallback, PostgreSQL-Pfad), Internationali-
  sierungs-Settings und `DEFAULT_AUTO_FIELD` unverändert – alles korrekt.

### `secpipeline/urls.py`
- **Toter Code (behoben):** Die Datei importierte `django.contrib.admin`
  und registrierte `path('admin/', admin.site.urls)` – obwohl
  `django.contrib.admin` nicht in `INSTALLED_APPS` steht und kein Web-Layer
  existiert. Der Admin-Endpunkt wäre nie erreichbar gewesen und hätte
  Leser irregeführt. Import und Route entfernt; Datei auf einen klaren
  Modul-Docstring und leere `urlpatterns = []` reduziert.

### `pipeline/tests/` (6 Testdateien)
- **Abdeckung:** alle sechs Module (downloader, parser, data_preparation,
  db_manager, validation, models) sind durch eigene Testklassen abgedeckt.
  Insgesamt 31 Tests.
- **Qualität:** DB-Tests (`TestCase`) vs. reine Logiktests (`SimpleTestCase`)
  korrekt getrennt. Netzwerk und Dateisystem werden konsequent gemockt
  (kein echter SEC-Zugriff, kein Schreiben in `data/`).
- Keine Bugs oder fehlenden Assertions gefunden. Keine Änderungen.

---

## 2.5 Querschnitt

### Ungenutzte Imports/Variablen
`pyflakes` meldet nach den Änderungen in 2.3 und 2.4 null Befunde:

```bash
python -m pyflakes pipeline/ secpipeline/ modules/ config.py main.py
# (keine Ausgabe)
```

### Einheitlicher Code-Stil
- PEP-8 wird in allen Dateien eingehalten (4-Spaces-Einrückung, snake_case,
  Imports alphabetisch gruppiert).
- Alle Module und Funktionen haben Docstrings (Pflicht laut CLAUDE.md).
- Sprache: Code/Docstrings Englisch, Dokumentation Deutsch – konsequent.

### Hardcoded-Werte
Nach diesem Review sind keine unbegründeten Hardcoded-Werte mehr vorhanden:

| Datei | Wert | Status |
|-------|------|--------|
| `config.py` | alle Pipeline-Werte | via `os.getenv()` überschreibbar |
| `secpipeline/settings.py` | `SECRET_KEY`, `DEBUG` | via `os.getenv()` überschreibbar (2.4 behoben) |
| `pipeline/models.py` | `max_length`, `max_digits` | DB-Schema-Konstanten, sinnvoll direkt |

### Tests
Alle 31 Tests laufen grün. Lokal ohne PostgreSQL-Server ausführen:

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=test_local.sqlite3 python manage.py test
```

Der SQLite-Fallback ist im `.env.example` dokumentiert und erzeugt ein
schema-identisches Schema – kein separater `manage.py migrate`-Schritt nötig.
