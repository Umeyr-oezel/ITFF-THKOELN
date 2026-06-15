# Plan B: Server-Alternative (PostgreSQL-Hosting)

**Erstellt:** 15.06.2026  
**Team:** Kenan & Matthias  
**Kontext:** Plan A ist der Uni-Server von Herrn Miebs. Falls dieser nicht bereitgestellt wird,
brauchen wir einen Plan B mit einer externen, kostenlosen PostgreSQL-Datenbank.

---

## 1. Anforderungen (3.1)

Fuer Plan B muss der Server folgende Kriterien erfuellen:

| Anforderung | Begruendung |
|---|---|
| Dauerhaft kostenlos (kein Trial, keine Kreditkarten-Falle) | Kein Budget vorhanden |
| Vollstaendige PostgreSQL-Datenbank (Version 13+) | Django-ORM nutzt PostgreSQL-spezifische Features |
| Ausreichend Speicher fuer ~4,6 Mio. Zeilen (geschaetzte 3-8 GB mit Indizes) | Vollstaendige Import-Pipeline 2020-2025 |
| Keine automatische Loeschung der Daten | Pipeline laeuft ueber mehrere Monate |
| Erreichbar von aussen (Remote-Verbindung per Django) | Pipeline-Import erfolgt nicht lokal auf dem Server |
| Praeferenz: Serverstandort EU | Datenschutz, DSGVO |
| Ausreichend Verbindungen fuer Django-Betrieb | Mindestens 5-10 gleichzeitige Verbindungen |

---

## 2. Recherche: Alle Kandidaten (3.2)

### 2.1 Ubersichtstabelle

| Anbieter | Dauerhaft gratis | Speicher | Max. Verbindungen | Auto-Pause | EU-Region | Geeignet fuer Projekt |
|---|---|---|---|---|---|---|
| **Neon** | JA | 0,5 GB | ~20 | 5 Min. (nicht abstellbar) | Frankfurt | **NEIN** (Speicher zu klein) |
| **Supabase** | JA | 0,5 GB | 60 direkt + 200 Pooler | 7 Tage Inaktivitaet | JA (mehrere) | **NEIN** (Speicher zu klein) |
| **Railway** | NEIN | — | — | — | — | NEIN |
| **Render** | NEIN (30 Tage) | 1 GB | — | Auto-Delete nach 30d | — | NEIN |
| **ElephantSQL** | GESCHLOSSEN | — | — | — | — | NEIN |
| **Aiven** | JA | 1 GB | 20 | JA (Inaktivitaet) | Frankfurt, Amsterdam | **NEIN** (Speicher zu klein) |
| **Fly.io Postgres** | NEIN | — | — | — | — | NEIN |

### 2.2 Detailanalyse je Kandidat

---

#### Neon (neon.tech)

- **Dauerhaft gratis:** JA – keine Kreditkarte, kein Ablaufdatum
- **Speicher:** 0,5 GB (aggregiert ueber alle Projekte: 5 GB auf bis zu 10 Projekte)
- **Verbindungen:** Nicht explizit veroeffentlicht, geschaetzte 10-20 gleichzeitige
- **PostgreSQL-Version:** 14, 15, 16
- **Auto-Pause:** JA – Scale-to-Zero nach **5 Minuten** Inaktivitaet (im Free Tier nicht abschaltbar). Cold Start: ca. 500 ms; Django-Verbindungen funktionieren trotzdem, weil der erste Request die Instanz reaktiviert
- **EU-Region:** JA – **Frankfurt (eu-central-1)** verfuegbar
- **Django-Integration:** Niedrige Komplexitaet. Offizielle Dokumentation vorhanden. `psycopg` (v3) empfohlen, `CONN_HEALTH_CHECKS: True` und `sslmode: require` setzen
- **Stand 2025-2026:** Aktiv. Im Mai 2025 von Databricks uebernommen; Compute-Budget im Free Tier verdoppelt (100 CU-Stunden/Monat)
- **Ausschlusskriterium:** 0,5 GB Speicher reichen fuer 4,6 Mio. Zeilen SEC-Daten **nicht aus**

---

#### Supabase (supabase.com)

- **Dauerhaft gratis:** JA – keine Kreditkarte erforderlich, max. 2 aktive Projekte
- **Speicher:** 500 MB Datenbank + 1 GB File Storage
- **Verbindungen:** 60 direkte + 200 ueber PgBouncer-Pooler (bereits integriert)
- **PostgreSQL-Version:** 13, 14, 15
- **Auto-Pause:** JA – pausiert nach **7 Tagen** Inaktivitaet. Daten bleiben erhalten, manuell reaktivierbar ueber Dashboard. Da die Pipeline regelmaessig laeuft, wird die Instanz aktiv gehalten
- **EU-Region:** JA – West EU, North EU u. a.
- **Django-Integration:** Mittel-niedrige Komplexitaet. Verbindung per `psycopg2` oder Standard-Connection-String; PgBouncer-Pooling ist bereits integriert
- **Stand 2025-2026:** Aktiv, keine wesentlichen Aenderungen am Free Tier
- **Keine automatischen Backups** im Free Tier
- **Ausschlusskriterium:** 500 MB Speicher reichen fuer das Projekt **nicht aus**

---

#### Railway (railway.app)

- **Stand:** Free Tier **abgeschafft seit Juli 2023**. Neues Konto erhaelt nur $5 Trial-Guthaben, danach Hobby-Plan ($5/Monat) oder Pro-Plan ($20/Monat)
- **Entscheidung: AUSGESCHLOSSEN** – kein dauerhafter Free Tier

---

#### Render (render.com)

- **Gratis PostgreSQL:** JA, aber mit **automatischer Loeschung nach 30 Tagen** + 14 Tage Kuendigungsfrist vor dem Loeschen
- **Entscheidung: AUSGESCHLOSSEN** – Datenbank wird nach 30 Tagen geloescht, unbrauchbar fuer ein Semesterprojekt

---

#### ElephantSQL (elephantsql.com)

- **Stand: DEFINITIV GESCHLOSSEN seit 27. Januar 2025**. Neue Registrierungen wurden bereits ab Mai 2024 gestoppt. Betreiber (CloudAMQP) hat sich auf RabbitMQ/LavinMQ konzentriert
- **Entscheidung: AUSGESCHLOSSEN** – existiert nicht mehr

---

#### Aiven (aiven.io)

- **Dauerhaft gratis:** JA – keine Kreditkarte, kein Ablaufdatum
- **Speicher:** 1 GB (im Mai 2025 von 5 GB auf 1 GB reduziert)
- **Verbindungen:** **Maximal 20 gleichzeitige Verbindungen** (davon nutzt Aiven intern einige)
- **PostgreSQL-Version:** 13, 14, 15, 16
- **Auto-Pause:** JA – pausiert bei Inaktivitaet (genaue Dauer nicht offiziell veroeffentlicht). Kein Connection Pooling, kein VPC, keine statische IP
- **EU-Region:** JA – **Frankfurt** und **Amsterdam** (DigitalOcean-Infrastruktur)
- **Django-Integration:** Niedrige Komplexitaet. Standard `psycopg2`-Verbindung, SSL erforderlich
- **Stand 2025-2026:** Aktiv, aber Speicher-Limit wurde halbiert
- **Ausschlusskriterium:** 1 GB Speicher reicht fuer 4,6 Mio. Zeilen SEC-Daten **nicht aus**; ausserdem nur 20 Verbindungen

---

#### Fly.io Postgres

- **Stand:** Free Tier **abgeschafft seit 2024**. Nur $5 Trial-Guthaben fuer neue Konten; regulaere Postgres-Instanz kostet mindestens ~$38/Monat
- **Entscheidung: AUSGESCHLOSSEN** – kein dauerhafter Free Tier

---

## 3. Kernbefund: Das Speicherproblem

**Kein verfuegbarer Free Tier in 2026 hat ausreichend Speicher fuer 4,6 Mio. Zeilen SEC EDGAR 2020-2025.**

Geschaetzter Speicherbedarf des Projekts:

| Komponente | Geschaetzter Bedarf |
|---|---|
| Rohdaten (4,6 Mio. Zeilen, ~20-30 Spalten) | 2-5 GB |
| Indizes (ACCESSION_NUMBER, Datum, CIK) | 0,5-2 GB |
| **Gesamt PostgreSQL** | **ca. 3-7 GB** |

Verfuegbarer Speicher der besten Free-Tier-Optionen: **0,5 GB (Neon/Supabase)** und **1 GB (Aiven)** – das deckt bestenfalls 10-30 % des Bedarfs.

---

## 4. Empfehlung und Alternativen (3.3 – zur Abstimmung mit Team & Betreuer)

### Situation

Plan B als reiner Free-Tier-PostgreSQL-Server ist fuer den **vollstaendigen Datensatz** (2020-2025, 4,6 Mio. Zeilen) **technisch nicht realisierbar** mit den derzeit am Markt verfuegbaren kostenlosen Angeboten.

### Empfohlene Wege (zur Abstimmung)

#### Favorit: Neon Free Tier + reduzierter Datensatz
- **Anbieter:** Neon (neon.tech), Frankfurt
- **Konfiguration:** Free Tier (0,5 GB), kein Kreditkarte erforderlich
- **Kompromiss:** Import nur fuer 1-2 ausgewaehlte Jahre statt 2020-2025 (z. B. nur 2024 und 2025)
- **Warum Neon:** Bestes Developer-Experience fuer Django, offizielle Dokumentation, Frankfurt-Region, dauerhaft gratis, kein Ablaufdatum, Eigentuemer Databricks gibt Stabilitaet
- **Auto-Pause:** Scale-to-Zero nach 5 Minuten ist kein Problem – Django reaktiviert die Instanz automatisch beim naechsten Request
- **Django-Verbindung:** Getestet per `DATABASE_URL` mit `psycopg` (v3) und `sslmode=require`

#### Reserve: Aiven Free Tier (Frankfurt)
- **Anbieter:** Aiven, Frankfurt
- **Konfiguration:** Free Tier (1 GB, max. 20 Verbindungen)
- **Kompromiss:** Noch weniger Daten als bei Neon moeglich, da nur 1 GB aber 20 Verbindungslimit eng ist
- **Warum Reserve:** Doppelter Speicher im Vergleich zu Neon, direkte PostgreSQL-Verbindung ohne Besonderheiten

#### Alternative: Neon Launch Plan ($19/Monat)
Falls das vollstaendige Dataset (2020-2025) benoetigt wird und Budget vorhanden ist:
- Neon Launch: $19/Monat, Storage praktisch unbegrenzt ($0,085/GB-Monat zusaetzlich), kein Auto-Pause
- Fuer 6 Monate ca. $114 Gesamtkosten

#### Alternative: GitHub Education Pack / Supabase for Students
Einige Universitaetsprogramme bieten Zugang zu erweiterten Free Tiers:
- **GitHub Education Pack** beinhaltet manchmal Cloud-Guthaben
- **Supabase** hat ein Programm fuer Studenten/Universitaeten
- **Empfehlung:** Herr Miebs fragen, ob die TH Koeln hier Optionen hat

---

## 5. Naechste Schritte

- [ ] Abstimmung mit Team und ggf. Herrn Miebs: Welcher Weg wird verfolgt?
- [ ] Entscheidung ob reduzierter Datensatz akzeptabel ist (Neon Free Tier) oder Vollimport benoetigt wird
- [ ] Pruefung ob GitHub Education Pack / Universitaets-Benefit verfuegbar ist
- [ ] Nach Entscheidung: Test-Verbindung Django -> gewaehter PostgreSQL-Server aufbauen (Aufgabe 4 vorbereiten)

---

## 6. Quellen

- Neon Preise & Dokumentation: neon.com/pricing, neon.com/docs/guides/django
- Supabase Free Tier Limits 2026: supabase.com/pricing
- Railway Pricing History: saaspricepulse.com
- Render PostgreSQL 2026: render.com/docs/databases
- ElephantSQL End-of-Life: elephantsql.com/blog/end-of-life-announcement.html
- Aiven Free Tier & Changelog: aiven.io/free-tier, aiven.io/changelog
- Fly.io Pricing 2026: fly.io/docs/about/pricing
- Vergleichsartikel 2026: koyeb.com/blog/top-postgresql-database-free-tiers-in-2026
