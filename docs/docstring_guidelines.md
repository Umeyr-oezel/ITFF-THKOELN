# Docstring-Richtlinien (Aufgabe 3)

Diese Doku haelt fest, wie wir im Projekt Docstrings schreiben. Sie gilt fuer
alle Module - egal wer den Code anfasst. Ziel ist ein einheitlicher, natuerlich
lesbarer Stil.

## Grundregeln

- **Jedes Modul** hat einen Docstring ganz oben, der kurz erklaert, wofuer das
  Modul da ist.
- **Jede Funktion** hat einen Docstring.
- Sprache: **Englisch** (wie der restliche Code). Nur die Doku unter `/docs` und
  `Plan.md` ist auf Deutsch.

## Stil: natuerlich, nicht formelhaft

Der Docstring erklaert das **Warum**, nicht nur das **Was**. Er liest sich wie
ein kurzer Hinweis von einem Menschen an den naechsten, nicht wie ein
generiertes Schema.

Gutes Beispiel aus dem Projekt (`parser.read_tsv`):

```python
def read_tsv(filepath):
    """Read a TSV into a DataFrame.

    Falls back to latin-1 if UTF-8 chokes. ACCESSION_NUMBER is
    forced to string - otherwise pandas might mangle it.
    """
```

Der erste Satz sagt knapp, was die Funktion tut. Danach folgt das Interessante:
*warum* latin-1, *warum* ACCESSION_NUMBER als String. Genau dieses
Hintergrundwissen ist wertvoll.

## Keine Args-/Returns-Bloecke

Wir benutzen **keine** `Args:` / `Returns:` / `Raises:`-Bloecke. Parameter und
Rueckgabewerte werden stattdessen natuerlich im Fliesstext erwaehnt, wenn sie
nicht offensichtlich sind.

Statt:

```python
def parse_all_quarters(zip_list):
    """Extract and parse all downloaded ZIPs.

    Args:
        zip_list: list of (quarter_label, zip_path) from downloader

    Returns dict: quarter_label -> parsed data dict.
    """
```

Lieber:

```python
def parse_all_quarters(zip_list):
    """Extract and parse all downloaded ZIPs.

    Takes the list of (quarter_label, zip_path) tuples from the
    downloader and returns a dict mapping each quarter_label to its
    parsed data dict.
    """
```

## Was wir NICHT dokumentieren

- **Django `class Meta`**: Das sind reine Konfigurationsklassen (Tabellenname,
  Indizes). Ein Docstring darauf waere kuenstlicher Ballast - so wuerde es auch
  kein Mensch schreiben. Sie bleiben bewusst ohne Docstring.
- Keine ueberfluessigen Kommentare, die das Offensichtliche wiederholen.
- Keine KI-Spuren (`# AI generated`, `# Created by ...` o.ae.).

## Kurzregel fuer Klassen

Models und andere echte Klassen bekommen einen Klassen-Docstring, der die Rolle
der Klasse erklaert. Standard-Methoden wie `__str__` bekommen einen kurzen
Docstring, wenn sie eine eigene Klasse haben. Die inneren `Meta`-Klassen sind
die einzige bewusste Ausnahme (siehe oben).
