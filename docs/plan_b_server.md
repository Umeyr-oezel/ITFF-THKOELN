# Plan B: Server-Alternative (PostgreSQL-Hosting)

**Erstellt:** 15.06.2026  
**Team:** Kenan & Matthias  
**Kontext:** Plan A ist der Uni-Server von Herrn Miebs. Falls dieser nicht bereitgestellt
wird, brauchen wir einen Plan B mit einem externen, kostenlosen PostgreSQL-Server.

---

## 1. Anforderungen (3.1)

| Anforderung | Begruendung |
|---|---|
| Dauerhaft kostenlos (kein Trial, keine Kreditkarte) | Kein Budget |
| Vollstaendige PostgreSQL-Datenbank (Version 13+) | Django-ORM-Kompatibilitaet |
| Ausreichend Speicher fuer optimierten Datensatz | Siehe Abschnitt 3 fuer genaue Berechnung |
| Keine automatische Datenloesch-Funktion | Pipeline laeuft ueber mehrere Monate |
| Remote-Zugriff (fuer Django-Pipeline) | Import erfolgt von ausserhalb des Servers |
| Praeferenz: EU-Serverstandort | Datenschutz, DSGVO |
| Mindestens 5-10 gleichzeitige Verbindungen | Django-Betrieb |

---

## 2. Kandidaten-Recherche (3.2)

### 2.1 Ubersichtstabelle (Stand: Juni 2026)

| Anbieter | Dauerhaft gratis | Speicher | Max. Verb. | Auto-Pause | EU-Region | Beurteilung |
|---|---|---|---|---|---|---|
| **Aiven** | JA | **1 GB** | 20 | JA (Inaktiv.) | Frankfurt, Amsterdam | **FAVORIT** |
| **Neon** | JA | **0,5 GB** | ~20 | 5 Min. | Frankfurt | **RESERVE** |
| **Supabase** | JA | 0,5 GB | 60+200 | 7 Tage | JA (mehrere) | Alternative |
| Railway | NEIN (seit 7/2023) | — | — | — | — | Ausgeschlossen |
| Render | NEIN (30d Limit) | — | — | Auto-Delete | — | Ausgeschlossen |
| ElephantSQL | GESCHLOSSEN (1/2025) | — | — | — | — | Ausgeschlossen |
| Fly.io Postgres | NEIN (seit 2024) | — | — | — | — | Ausgeschlossen |

### 2.2 Detailanalyse der relevanten Kandidaten

---

#### Aiven (aiven.io) — FAVORIT

| Kriterium | Detail |
|---|---|
| **Dauerhaft gratis** | JA – keine Kreditkarte, kein Ablaufdatum |
| **Speicher** | 1 GB (seit Mai 2025, vorher 5 GB) |
| **Verbindungen** | Max. 20 gleichzeitig (Aiven nutzt intern einige) |
| **PostgreSQL-Version** | 13, 14, 15, 16 |
| **Auto-Pause** | JA bei laengerer Inaktivitaet (genaue Dauer nicht offiziell) |
| **EU-Region** | JA – **Frankfurt** und **Amsterdam** (DigitalOcean-Infrastruktur) |
| **Django-Integration** | Niedrige Komplexitaet – Standard-`psycopg2`-Connection, SSL erforderlich |
| **Stand 2026** | Aktiv, keine weiteren Aenderungen angekuendigt |
| **Besonderheiten** | Kein Connection Pooling, kein VPC, keine statische IP im Free Tier |

**Warum Favorit:** Mit 1 GB Speicher und geschickter Datenkonfiguration laesst sich der
Kern des Projekts komplett abbilden (Details in Abschnitt 3). Frankfurt-Region, dauerhaft
gratis, Standard-PostgreSQL-Verbindung ohne Sonderlocken.

---

#### Neon (neon.tech) — RESERVE

| Kriterium | Detail |
|---|---|
| **Dauerhaft gratis** | JA – keine Kreditkarte, kein Ablaufdatum |
| **Speicher** | 0,5 GB (5 GB aggregiert ueber max. 10 Projekte) |
| **Verbindungen** | Nicht offiziell publiziert; ca. 10-20 gleichzeitig |
| **PostgreSQL-Version** | 14, 15, 16 |
| **Auto-Pause** | JA – Scale-to-Zero nach **5 Minuten** Inaktivitaet (nicht abschaltbar im Free Tier); Cold Start ca. 500 ms |
| **EU-Region** | JA – **Frankfurt (eu-central-1)** |
| **Django-Integration** | Sehr niedrig – offizielle Dokumentation, `psycopg` v3 empfohlen, `CONN_HEALTH_CHECKS: True` |
| **Stand 2026** | Aktiv; Mai 2025 von Databricks uebernommen – Compute-Budget verdoppelt |
| **Besonderheiten** | Bestes Developer-Experience fuer Django von allen Kandidaten; Auto-Pause reaktiviert sich automatisch beim naechsten Django-Request |

**Warum Reserve:** Weniger Speicher als Aiven (0,5 GB vs. 1 GB), aber beste Django-Dokumentation
und Databricks-Rueckhalt sorgen fuer langfristige Stabilitaet. Als Reserve bei Aiven-Problemen
sofort einsetzbar.

---

#### Supabase (supabase.com) — Alternative bei Bedarf

Gleicher Speicher wie Neon (0,5 GB), aber Auto-Pause erst nach 7 Tagen (toleranter als
Neons 5 Minuten). PgBouncer-Pooling bereits integriert (200 Verbindungen ueber Pooler).
Als dritte Option falls Aiven und Neon beide ausscheiden.

---

## 3. Speicheroptimierung: Realistische Kalkulation

### 3.1 Korrektur der frueheren Schaetzung

Die initiale Schaetzung von 3-8 GB war zu hoch. Sie basierte auf einer Worst-Case-Annahme
fuer alle Rohdaten. Die genaue Analyse der Django-Modelle und der Datenmenge ergibt ein
realistischeres Bild:

**Tatsaechliche Zeilenverteilung (4,6 Mio. gesamt, 2020-2025, 24 Quartale):**

| Tabelle | Geschaetzte Zeilen | Grund |
|---|---|---|
| `submissions` | ~1,85 Mio. | ~77.000 Form-4-Filings pro Quartal |
| `nonderiv_trans` | ~1,85 Mio. | ~1 Transaktion/Filing im Schnitt |
| `nonderiv_holdings` | ~460.000 | Etwa 25% der Submissions |
| `deriv_trans` | ~280.000 | Derivate-Transaktionen (seltener) |
| `deriv_holdings` | ~185.000 | Derivate-Bestands-Snapshots |
| `validation_log` | ~150.000 | Ca. 5% der Transaktionszeilen |
| `pipeline_log` | ~100 | Laufprotokoll, minimal |

### 3.2 PostgreSQL-Speicher pro Tabelle

| Tabelle | Bytes/Zeile | Zeilen | Daten | Indizes | Gesamt |
|---|---|---|---|---|---|
| `submissions` | ~170 | 1,85 Mio. | 315 MB | 80 MB | **395 MB** |
| `nonderiv_trans` | ~148 | 1,85 Mio. | 274 MB | 60 MB | **334 MB** |
| `nonderiv_holdings` | ~80 | 460.000 | 37 MB | 8 MB | **45 MB** |
| `deriv_trans` | ~148 | 280.000 | 41 MB | 12 MB | **53 MB** |
| `deriv_holdings` | ~80 | 185.000 | 15 MB | 3 MB | **18 MB** |
| `validation_log` | ~150 | 150.000 | 22 MB | 8 MB | **30 MB** |
| `pipeline_log` | ~100 | 100 | <1 MB | — | ~1 MB |
| **GESAMT** | | **4,6 Mio.** | **704 MB** | **171 MB** | **~876 MB** |

### 3.3 Konfigurationsszenarien nach Anbieter

#### Szenario A — Aiven (1 GB): 5 Jahre, alle Tabellen (EMPFOHLEN)

```
# .env
START_YEAR=2021
END_YEAR=2025
```

| Tabelle | Faktor | Geschaetzter Speicher |
|---|---|---|
| Alle 7 Tabellen, 5/6 der Daten | 5/6 × 876 MB | **~730 MB** |

→ **730 MB von 1.024 MB** (71 % belegt, 294 MB Puffer)  
→ Vollstaendige Analyse 2021-2025 moeglich — nur 2020 fehlt

---

#### Szenario B — Neon (0,5 GB): 3 Jahre, alle Tabellen (EMPFOHLEN als Reserve)

```
# .env
START_YEAR=2023
END_YEAR=2025
```

| Tabelle | Faktor | Geschaetzter Speicher |
|---|---|---|
| Alle 7 Tabellen, 3/6 der Daten | 3/6 × 876 MB | **~438 MB** |

→ **438 MB von 512 MB** (86 % belegt, ~74 MB Puffer)  
→ Vollstaendige Analyse 2023-2025 (3 Jahre) moeglich

---

#### Szenario C — Neon (0,5 GB): 4 Jahre, ohne Holdings-Tabellen (Puffer-Variante)

Falls Szenario B zu knapp wird, koennen die Holdings-Tabellen weggelassen werden.
`evaluation.py` importiert `NonderivHolding` und `DerivHolding` **nicht** — die
Evaluation laeuft ohne sie vollstaendig durch.

```
# .env
START_YEAR=2022
END_YEAR=2025
```

| Tabellen | Faktor | Geschaetzter Speicher |
|---|---|---|
| submissions + nonderiv_trans + deriv_trans + validation_log + pipeline_log | 4/6 × (876 - 63) MB | **~542 MB** ← zu gross |

Besser: nur 3 Jahre ohne Holdings:

```
# .env
START_YEAR=2023
END_YEAR=2025
```

→ 3/6 × 813 MB = **~407 MB** (79 % von 0,5 GB) – komfortabler Puffer

---

### 3.4 Welche Tabellen sind fuer die Evaluation zwingend?

Aus `evaluation.py` (importierte Modelle):

| Tabelle | Benoetigt | Begruendung |
|---|---|---|
| `submissions` | **JA** | Issuer, Ticker, Datum, Owner-Typ |
| `nonderiv_trans` | **JA** | Kern-Transaktionen (Kaufe/Verkaufe, Volumen) |
| `deriv_trans` | **JA** | Wird in Evaluation-Queries einbezogen |
| `validation_log` | **JA** | `is_valid`-Flag steuert welche Zeilen ausgewertet werden |
| `pipeline_log` | **JA** | Audit-Trail; sehr klein |
| `nonderiv_holdings` | optional | Wird von `evaluation.py` **nicht** importiert |
| `deriv_holdings` | optional | Wird von `evaluation.py` **nicht** importiert |

---

## 4. Empfehlung (3.3 – zur Abstimmung mit Team & Betreuer)

### Favorit: Aiven Free Tier — Frankfurt

- **Anbieter:** Aiven (aiven.io)
- **Region:** Frankfurt oder Amsterdam
- **Konfiguration:** `START_YEAR=2021`, `END_YEAR=2025` in `.env`
- **Datenmenge:** ~5 Jahre, alle 7 Tabellen
- **Speicher:** ~730 MB von 1.024 MB (71 %)
- **Einrichtungsaufwand:** Gering — Standard-`psycopg2`, SSL, keine Kreditkarte
- **Verbindungslimit:** 20 gleichzeitig — ausreichend fuer den Pipeline-Betrieb
- **Kosten:** 0 €

**Vorteil gegenueber Neon:** Mehr Speicher = mehr Jahre = bessere Trendanalyse.  
**Nachteil:** Kein offizielles Django-Tutorial, 20 Verbindungslimit, Auto-Pause-Dauer unklar.

---

### Reserve: Neon Free Tier — Frankfurt

- **Anbieter:** Neon (neon.tech)
- **Region:** Frankfurt (eu-central-1)
- **Konfiguration:** `START_YEAR=2023`, `END_YEAR=2025` in `.env`
- **Datenmenge:** 3 Jahre, alle 7 Tabellen
- **Speicher:** ~438 MB von 512 MB (86 %)
- **Einrichtungsaufwand:** Sehr gering — offizielle Django-Dokumentation vorhanden
- **Verbindungslimit:** ~10-20 gleichzeitig — ausreichend
- **Auto-Pause:** 5 Minuten Inaktivitaet → Django reaktiviert automatisch beim naechsten Request, kein manuelles Eingreifen noetig
- **Kosten:** 0 €

**Vorteil gegenueber Aiven:** Beste Django-Unterstuetzung, Databricks-Backing als Stabilitaetsgarantie.  
**Nachteil:** Nur 3 Jahre (nicht 5-6), 0,5 GB ist eng bemessen.

---

## 5. Konfiguration im Projekt (keine Code-Aenderung noetig)

Die Jahreszahl-Steuerung ist bereits ueber `config.py` und `.env` vorhanden:

```python
# config.py (bereits so implementiert)
START_YEAR = int(os.getenv("START_YEAR", 2020))
END_YEAR   = int(os.getenv("END_YEAR", 2025))
```

Fuer Aiven (Plan B) einfach in `.env` setzen:
```
START_YEAR=2021
END_YEAR=2025
```

Fuer Neon (Reserve):
```
START_YEAR=2023
END_YEAR=2025
```

Keine weiteren Code-Aenderungen noetig. Die Pipeline laedt dynamisch alle
verfuegbaren Quartale des konfigurierten Zeitraums.

---

## 6. Ausstehende Schritte (nach Team-Abstimmung)

- [ ] Team-Abstimmung: Aiven oder Neon als Plan B — welcher Zeitraum ist akzeptabel?
- [ ] Konto beim gewaehlten Anbieter anlegen (kein Budget erforderlich)
- [ ] Django-Testverbindung aufbauen (`DATABASE_URL` in `.env` setzen, `python manage.py migrate` testen)
- [ ] Kurz-Pipeline-Lauf mit 1 Quartal (Datenmenge und Verbindung verifizieren)
- [ ] Danach: Aufgabe 4 (vollstaendige DB-Migration) starten

---

## 7. Quellen

- Aiven Free Tier & Changelog (Storage-Reduzierung Mai 2025): aiven.io/free-tier, aiven.io/changelog
- Aiven PostgreSQL Connection Limits: aiven.io/docs/products/postgresql/reference/pg-connection-limits
- Neon Preise & Free Tier: neon.com/pricing
- Neon Django-Dokumentation: neon.com/docs/guides/django
- Neon Scale-to-Zero: neon.com/docs/introduction/scale-to-zero
- Supabase Free Tier 2026: supabase.com/pricing
- Railway (kein Free Tier): railway.app/pricing
- Render (30-Tage-Limit): render.com/docs/databases
- ElephantSQL End-of-Life (Jan. 2025): elephantsql.com/blog/end-of-life-announcement.html
- Fly.io (kein Free Tier seit 2024): fly.io/docs/about/pricing
- Vergleichsartikel 2026: koyeb.com/blog/top-postgresql-database-free-tiers-in-2026
