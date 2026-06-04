# Lokaler SQLite-Fallback und Unit-Tests

Diese Doku erklaert zwei Erweiterungen, die zusammengehoeren: einen
lokalen **SQLite-Fallback** fuer die Datenbank und eine **Test-Suite**,
die genau diesen Fallback nutzt. Beides ist nur moeglich, weil das
Projekt seit Aufgabe 2 das **Django ORM** verwendet.

## Warum das Ganze?

Bis die echten PostgreSQL-Zugangsdaten vom Kurs-Server vorliegen, war
lokales Testen blockiert: ohne erreichbare Datenbank laufen weder
`migrate` noch die Pipeline noch sinnvolle Tests.

Der Trick: Weil wir das Django ORM nutzen, ist die Datenbank
**austauschbar**. Derselbe Code und dieselben Migrationen funktionieren
auf PostgreSQL genauso wie auf SQLite. SQLite ist dabei nur eine einzelne
Datei auf der Festplatte - kein Server, keine Zugangsdaten.

## Der SQLite-Fallback

### Wie man umschaltet

In der `.env` (Vorlage siehe `.env.example`) die PostgreSQL-Zeilen
auskommentieren und stattdessen diese beiden aktivieren:

```
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=local.sqlite3
```

Danach baut ein Befehl die komplette Datenbankstruktur lokal auf:

```
python manage.py migrate
```

Es entstehen alle 7 Tabellen (`submissions`, `nonderiv_trans`,
`nonderiv_holdings`, `deriv_trans`, `deriv_holdings`, `validation_log`,
`pipeline_log`) - exakt dieselben wie auf PostgreSQL.

### Wichtig: PostgreSQL bleibt der Standard

In `secpipeline/settings.py` ist PostgreSQL weiterhin die Vorgabe. Der
SQLite-Zweig greift nur, wenn `DB_ENGINE` ausdruecklich auf den
SQLite-Backend gesetzt wird. Fuer die echte Abgabe sollte trotzdem einmal
gegen den PostgreSQL-Server gelaufen sein - SQLite ist zum lokalen Testen
gedacht, ist aber nicht bit-fuer-bit identisch mit PostgreSQL (z.B. ist es
lockerer bei Datentypen).

### Die DB-Datei kommt nicht auf GitHub

`*.sqlite3` steht in `.gitignore`. Die Datenbankdatei ist - genau wie der
`data/`-Ordner - lokal und wird nie committet. Jeder erzeugt sie selbst
mit `migrate`. So landen auch keine Daten oder Zugangsdaten im Repo.

## Die Unit-Tests

### Ausfuehren

```
python manage.py test
```

Django baut sich dafuer automatisch eine **temporaere** SQLite-Test-DB,
laesst die Tests laufen und wirft sie wieder weg. Damit laufen die Tests
ohne PostgreSQL-Server und ohne Zugangsdaten. Voraussetzung ist nur, dass
der SQLite-Fallback in der `.env` aktiv ist (siehe oben).

Es wird **kein zusaetzliches Paket** gebraucht - das Test-Framework ist
in Django eingebaut.

### Was getestet wird

Die Tests liegen unter `pipeline/tests/`, eine Datei pro Modul:

| Datei | Geprueft |
|-------|----------|
| `test_data_preparation.py` | Spalten-Cleaning, SEC-Datumsparsing, Owner-Merge mit Rollen-Flags, Nominalvolumen, Metadaten |
| `test_validation.py` | Alle 8 Plausibilitaetschecks (4 Pflicht + 4 Bonus) - je eine gute und eine schlechte Zeile |
| `test_parser.py` | TSV-Lesen (inkl. ACCESSION_NUMBER als String), fehlende/leere Dateien, JSON, ZIP-Extraktion |
| `test_downloader.py` | Quartals-Erkennung per Scraping (Netzwerk gemockt), lokale Datei-Lookups, Retry bei Server-Fehler |
| `test_db_manager.py` | Idempotenz (zweimal importieren = gleiches Ergebnis), Pipeline-Log waechst, Orphan-Zeilen werden verworfen |
| `test_models.py` | `__str__`, echtes Foreign-Key-CASCADE beim Loeschen |

Stand: 30 Tests, alle gruen.

### Warum diese Tests sinnvoll sind

- Die **Idempotenz** (Delete-then-Insert) ist das Herz der Pipeline -
  jetzt automatisch abgesichert.
- Die **8 Validierungschecks** sind die Datenqualitaet des Projekts - ein
  versehentliches Umdrehen einer Bedingung faellt jetzt sofort auf.
- Netzwerk und Datenbank sind **gemockt bzw. temporaer** - die Tests sind
  schnell (< 1 Sekunde) und brauchen weder Internet noch den Kurs-Server.

## Offener Punkt (fuer Aufgabe 6 / Bugsuche)

Beim Testen ist ein Edge-Case aufgefallen: `prepare_transactions` und
`prepare_holdings` rufen `_clean_columns` auf, **bevor** sie auf eine leere
DataFrame pruefen. Bei einer voellig spaltenlosen leeren DataFrame - wie
`read_tsv` sie bei einer fehlenden Datei zurueckgibt - bricht das mit einem
`AttributeError` ab. In der Praxis liefern SEC-Quartale immer alle Dateien,
deshalb ist es bisher nie aufgetreten. Der Fix ist klein (erst auf
`df.empty` pruefen, dann reinigen), wurde aber bewusst **nicht** umgesetzt:
Bugsuche ist Aufgabe 6 und Teamaufgabe.
