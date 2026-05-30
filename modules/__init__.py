"""Pipeline modules for the SEC Form 4 workflow.

Each stage lives in its own module: downloading, parsing, data
preparation, the database layer, validation, and evaluation. The
database modules talk to PostgreSQL through the Django ORM, so they
must only be imported after django.setup() has run (main.py handles
that before importing anything here).
"""
