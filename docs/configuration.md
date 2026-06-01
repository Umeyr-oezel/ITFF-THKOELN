# Konfiguration der Pipeline

Alle konfigurierbaren Werte der Pipeline sind in zwei Dateien zentralisiert:
`config.py` fuer Code-Konfiguration und `.env` fuer umgebungsspezifische Werte.

---

## .env — Umgebungsvariablen

Wird lokal angelegt (nie auf GitHub). Vorlage: `.env.example`.

| Variable | Standard | Beschreibung |
|---|---|---|
| `DB_ENGINE` | `django.db.backends.postgresql` | Django-Datenbanktyp |
| `DB_NAME` | `group01` | Datenbankname |
| `DB_HOST` | `localhost` | Datenbankserver |
| `DB_PORT` | `5432` | Datenbankport |
| `DB_USER` | — | Datenbanknutzer |
| `DB_PASSWORD` | — | Datenbankpasswort |
| `START_YEAR` | `2020` | Erstes Jahr der Datenabfrage |
| `END_YEAR` | `2025` | Letztes Jahr der Datenabfrage |
| `USER_AGENT` | `University Group01 ...` | HTTP-Header fuer SEC-Anfragen |
| `REQUEST_DELAY` | `0.2` | Wartezeit zwischen SEC-Requests (Sekunden) |
| `CREATED_BY` | `group01` | Wert fuer die `created_by`-Spalte in der DB |
| `MAX_RETRIES` | `3` | Maximale Wiederholungsversuche bei Download-Fehlern |
| `MAX_REASONABLE_PRICE` | `1000000` | Schwellenwert fuer unrealistische Aktienpreise |

---

## config.py — Code-Konfiguration

Werte die sich nicht per Umgebungsvariable aendern lassen (oder keinen Sinn ergaeben).

| Konstante | Beschreibung |
|---|---|
| `SEC_BASE_URL` | URL der SEC-Seite mit den ZIP-Dateien |
| `TARGET_YEARS` | Liste der Jahre aus `START_YEAR` bis `END_YEAR` |
| `BATCH_SIZE` | Datensaetze pro DB-Insert-Batch (Standard: 5000) |
| `KNOWN_TRANS_CODES` | Set aller gueltigen SEC Form 4 Transaktionscodes |
| `CHART_COLORS` | Farbschema fuer alle Charts (Dictionary) |
| `LOGO_PATH` | Pfad zum TH-Koeln-Logo fuer Chart-Branding |
| `MONTH_NAMES` | Mapping Monatsnummer → Monatsname (Englisch) |

---

## Verzeichnisstruktur (hardcoded, nicht konfigurierbar)

```
data/raw/           ZIP-Dateien von SEC
data/extracted/     Entpackte TSV-Dateien
output/charts/      Generierte Charts
output/tables/      CSV-Exporte
logs/               Pipeline-Logs
```

Diese Pfade sind bewusst fest eingebaut — sie aendern sich nicht zwischen
Umgebungen und eine Konfigurierbarkeit wuerde keinen Mehrwert bringen.
