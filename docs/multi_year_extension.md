# Aufgabe 5: Historie erweitern – 2020 bis 2025

## Was wurde gemacht

Die Pipeline verarbeitete zuvor nur ein einzelnes Jahr (`TARGET_YEAR = 2025`). Sie wurde so umgebaut, dass sie dynamisch mehrere Jahre abdeckt.

---

## Änderungen im Überblick

### config.py
`TARGET_YEAR` wurde durch `TARGET_YEARS` ersetzt:

```python
CURRENT_YEAR = datetime.now().year
TARGET_YEARS = list(range(CURRENT_YEAR - 4, CURRENT_YEAR + 1))
```

Die Liste ergibt sich automatisch aus dem aktuellen Jahr. Kein Hardcoding mehr.

### downloader.py
`get_available_quarters()` und `list_existing_quarters()` durchsuchen die SEC-Seite jetzt nach allen Jahren in `TARGET_YEARS`. Der Regex-Pattern wird dynamisch aus der Jahresliste gebaut.

### parser.py / data_preparation.py
Keine Änderungen nötig. Beide Module arbeiten mit Quarter-Labels wie `"2020Q1"` und waren bereits multi-year kompatibel.

### db_manager.py
Keine Änderungen nötig. Der Import ist idempotent pro Quartal und funktioniert für beliebig viele Quartale.

### evaluation.py
Alle Funktionen bekamen einen `year`-Parameter. Neue Struktur:

- `generate_all_evaluations(years=None)` — loopt über alle Ziel-Jahre
- `generate_evaluations_for_year(engine, year)` — erstellt Charts, CSVs und PDF für ein einzelnes Jahr
- Pro Jahr: 3 Übersichts-Charts, monatliche Bar-Charts, CSV-Tabellen, ein PDF-Report

Dateinamen und Ordnerstruktur enthalten das Jahr, z.B. `2023-01/`, `2023_trend_volume.png`, `2023_evaluation_report.pdf`.

### main.py
Neue CLI-Flags:

```bash
python main.py                    # alle TARGET_YEARS (Standard)
python main.py --year 2023        # nur ein Jahr
python main.py --years 2020-2025  # beliebige Spanne
```

Neue Hilfsfunktion `resolve_years()` übersetzt die CLI-Eingabe in eine Jahresliste.

### modules/__init__.py
Pre-existierender Bug behoben: `get_engine` wurde bisher nicht korrekt re-exportiert, alle Module die es importierten hätten beim Start gecrasht.

---

## Ausgabestruktur

```
output/
  charts/
    monthly/
      2022-01/   ← pro Monat, pro Jahr
      2023-01/
      ...
    overview/
      2022_trend_volume.png
      2022_sentiment_index.png
      2022_repeat_sellers_heatmap.png
      2023_trend_volume.png
      ...
  tables/
    monthly/
      2022-01/
      ...
  2022_evaluation_report.pdf
  2023_evaluation_report.pdf
  ...
```
