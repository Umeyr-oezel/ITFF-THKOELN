"""Test suite for the SEC Form 4 pipeline.

The tests run against a throwaway SQLite database (Django spins one up
automatically), so the whole suite works without the PostgreSQL server -
just run `python manage.py test` with the SQLite fallback active.
"""
