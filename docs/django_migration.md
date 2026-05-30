# Django-Umstellung (Aufgabe 2)

Diese Doku beschreibt, wie die Pipeline von rohem SQL (SQLAlchemy + MySQL)
auf das Django ORM mit PostgreSQL umgestellt wurde. Sie richtet sich an alle
Projektmitglieder - auch an die, die nicht am Code beteiligt waren.

## Warum?

Vorher hat die Pipeline SQL-Strings von Hand gebaut und ueber SQLAlchemy an
einen geteilten MySQL-Server geschickt. Das hatte mehrere Nachteile:

- Das Datenbankschema lag als handgeschriebenes `CREATE TABLE` in `db_manager.py`.
- Fremdschluessel konnten auf dem Uni-Server oft nicht gesetzt werden (fehlendes
  REFERENCES-Recht), also musste die Integritaet im Code abgesichert werden.
- Viele Workarounds fuer den geteilten Server (Lock-Timeouts, Retry-Schleifen).

Mit Django liegt das Schema als Python-Modelle vor, Migrations verwalten die
Datenbank, und PostgreSQL erzwingt die Fremdschluessel sauber.

## Neue Struktur

```
secpipeline/        # Django-Projekt (nur Konfiguration)
    settings.py     # DB-Verbindung aus .env, ORM-only (kein Web/Auth)
pipeline/           # Django-App
    models.py       # die 7 Tabellen als Models
    migrations/     # 0001_initial.py
manage.py           # Django-Verwaltungsbefehle
```

Django wird hier **nur als ORM** verwendet - es gibt keine Webseite, kein Login
und kein Admin-Panel. In `settings.py` sind deshalb nur `django.contrib.contenttypes`
und unsere App `pipeline` aktiv. Das haelt die Datenbank frei von ungenutzten
Tabellen.

## Die Models (pipeline/models.py)

Sieben Models, eins pro Tabelle. Die Tabellennamen bleiben ueber `Meta.db_table`
exakt gleich (`submissions`, `nonderiv_trans`, ...).

- `Submission` - die Eltern-Tabelle, Primaerschluessel ist `accession_number`.
- `NonderivTrans`, `NonderivHolding`, `DerivTrans`, `DerivHolding` - haengen ueber
  einen echten Fremdschluessel (`ON DELETE CASCADE`) an `Submission`.
- `ValidationLog`, `PipelineLog` - stehen fuer sich. `pipeline_log` ist ein
  Audit-Log und wird nie geloescht.

Der Fremdschluessel nutzt `db_column="accession_number"`, damit die Spalte
genauso heisst wie vorher.

## Datenbank-Zugang (.env)

Die Zugangsdaten stehen ausschliesslich in der lokalen `.env` (niemals auf
GitHub). `settings.py` liest sie:

```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=group01
DB_HOST=...
DB_PORT=5432
DB_USER=...
DB_PASSWORD=...
```

Vorlage ist `.env.example`. Solange die echten PostgreSQL-Zugangsdaten noch
nicht vorliegen, stehen in `.env` Platzhalter (siehe Plan.md Abschnitt 2.8).

## Was sich im Code geaendert hat

**db_manager.py** - kein SQLAlchemy-Engine mehr. Der Import laeuft ueber
`bulk_create`, das Loeschen ueber `filter().delete()`. Ein Quartal wird in einer
Transaktion (`transaction.atomic`) importiert - der alte Workaround mit einzelnen
Transaktionen pro Tabelle entfaellt, weil PostgreSQL auf der eigenen DB nicht das
Lock-Problem des geteilten Servers hat. Neu: Transaktionen ohne passende
Submission (Orphans) werden vor dem Insert herausgefiltert und geloggt, weil der
echte Fremdschluessel sie sonst ablehnen wuerde.

**validation.py** - die 8 Pruefungen selbst sind unveraendert (sie arbeiten wie
vorher vektorisiert auf einem pandas-DataFrame). Geaendert wurde nur, wie die
Daten geladen (ORM statt LEFT JOIN) und zurueckgeschrieben werden (`bulk_update`
und `bulk_create`). Der Orphan-Check bleibt als Sicherheitsnetz erhalten, findet
durch den echten Fremdschluessel aber im Normalfall nichts mehr.

**evaluation.py** - alle Abfragen laufen ueber das ORM. Gruppierungen nutzen
`values().annotate()`, das MySQL-spezifische `MONTH()`/`YEAR()` wurde durch
`ExtractMonth` und den `trans_date__year`-Lookup ersetzt. Die Charts und der
PDF-Report sind unveraendert.

**config.py** - `DB_CONFIG` und `SCHEMA_NAME` sind raus; die Verbindung kommt
jetzt aus den Django-Settings. Uebrig bleiben nur nicht-sensible Einstellungen
(SEC-URL, Pfade, Batch-Groesse).

**main.py** - ruft ganz am Anfang `django.setup()` auf (noch vor den
Modul-Importen, da die Module das ORM nutzen). Der Vorab-Check prueft die
Datenbank jetzt ueber `django.db.connection`.

## Befehle

```bash
# Migration einmalig erstellen (schon geschehen: 0001_initial.py)
python manage.py makemigrations pipeline

# Schema in die Datenbank schreiben (braucht echten DB-Zugang)
python manage.py migrate

# Pipeline starten
python main.py --skip-download
```

## Aktueller Stand

Die komplette Code-Umstellung ist fertig und laeuft ohne Fehler durch die
Vorab-Checks (`manage.py check`, `makemigrations`, Import aller Module). Der
vollstaendige Durchlauf gegen eine echte PostgreSQL-Datenbank steht noch aus -
er ist erst moeglich, sobald die Zugangsdaten vorliegen.
