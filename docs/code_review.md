# Code-Review (Aufgabe 2) – Befunde und Fixes

Dieses Dokument hält das datei-für-datei-Review aus Aufgabe 2 fest. Für
jede Datei steht hier, was geprüft wurde (Effizienz, Hardcoded-Werte,
Bugs), was geändert wurde und warum. Geprüft wird von Team 2 (Kenan,
Matthias).

**Stand:** Aufgabe 2 ist inhaltlich durch – **2.2 (Root-Dateien)**,
**2.3 (`modules/`)**, **2.4 (Django-Dateien)**, **2.5 (Querschnitt)** und
**2.6 (diese Doku)**.

Die Tests (`python manage.py test`) laufen nach allen Änderungen
vollständig grün durch (34 Tests).

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

## 2.4 Django-Dateien

Weitere abgestimmte Entscheidungen (Absprache): **E** = `urls.py` aufräumen,
**F** = `SECRET_KEY`/`DEBUG` nach `.env`, **G** = `top_n_by`-Test ergänzen –
alle drei umgesetzt.

### `pipeline/models.py`
- Sauber und gut dokumentiert: `submissions` als Eltern-Tabelle, die vier
  Kind-Tabellen hängen über einen echten Foreign Key mit `CASCADE` daran,
  passende Indizes sind gesetzt. Keine Bugs, nichts geändert.

### `pipeline/admin.py`, `pipeline/apps.py`, `pipeline/views.py`
- Bewusst leer bzw. Standard-AppConfig – das Projekt nutzt Django nur als
  ORM (kein Web-Frontend, kein Admin). Korrekt dokumentiert, nichts zu tun.

### `pipeline/migrations/0001_initial.py`
- Auto-generiert und deckungsgleich mit den Modellen. Migrationen werden
  nicht von Hand bearbeitet – nur geprüft.

### `secpipeline/urls.py` (Entscheidung E)
- **Aufgeräumt:** War noch das Django-Default-Boilerplate mit langem
  Beispiel-Docstring und einer `admin/`-Route auf `admin.site.urls`. Problem:
  `django.contrib.admin` steht gar nicht in `INSTALLED_APPS`, und
  `settings.py` setzt kein `ROOT_URLCONF` – die Datei war also komplett
  unverdrahtet und verwies auf eine nicht installierte App. Jetzt: leere
  `urlpatterns = []` plus kurzer Docstring „kein Web-Layer" (konsistent zu
  `views.py`/`admin.py`).

### `secpipeline/settings.py` (Entscheidung F)
- **Hardcoded (behoben):** `SECRET_KEY` und `DEBUG` standen fest im Code.
  Beide kommen jetzt aus `.env` (`os.getenv`), mit dem bisherigen Wert als
  Fallback, damit Test-Suite und SQLite-Setup **ohne** `.env` weiterlaufen.
  In `.env.example` ergänzt. Praktisches Risiko war gering (kein Web-Layer,
  der den Key nutzt), aber es ist genau die Art Wert, die nach `.env` gehört –
  passend dazu, dass die DB-Zugangsdaten dort schon liegen.

### `pipeline/tests/*` (Entscheidung G)
- Bestehende Tests sind solide: Cascade-Delete, Import-Idempotenz,
  Audit-Log, Orphan-Drop, Daten-Aufbereitung, Parser, Downloader-Retry und
  alle 8 Validierungs-Checks.
- **Neu:** `pipeline/tests/test_evaluation.py` testet die neue Funktion
  `top_n_by` aus dem C-Refactor (reines pandas, ohne DB): höchste Werte
  zuerst, Begrenzung auf `TOP_N`, NULL-Werte landen hinten. Damit ist die
  pandas-Seite des Refactors testseitig abgesichert (die DB-seitige
  Gleichheit bleibt der visuelle Lauf gegen echte Daten, s. o.).

---

## 2.5 Querschnitt (über alle Dateien)

- **Ungenutzte Imports:** `seaborn` (evaluation.py) und `datetime`
  (data_preparation.py) entfernt; `py_compile` läuft über alle Module sauber.
- **Code-Stil:** PEP-8, englische Namen/Docstrings, jede Funktion und jedes
  Modul hat einen Docstring – beim Review eingehalten.
- **Keine neuen Hardcoded-Werte:** Die ausgelagerten Werte (`BATCH_SIZE`,
  `TOP_N`, `SECRET_KEY`, `DEBUG`) liegen jetzt zentral in `config.py`/`.env`.
- **Bugfixes durch Tests abgesichert:** `manage.py test` bleibt grün
  (**34 Tests**), inkl. des neuen `top_n_by`-Tests.

---

## Offen nach Aufgabe 2

- **Visueller Output-Vergleich** des C-Refactors gegen echte Daten (s. o.).
- Reine **Performance-Themen** (Voll-Load der Tabelle in `validation.py`,
  Query-Profiling) gehören zu Aufgabe 4.3 und brauchen den echten
  PostgreSQL-Server.
