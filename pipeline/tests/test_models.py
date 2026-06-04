"""Smoke tests for the ORM models themselves.

Mostly a sanity check that the foreign key really cascades now - the old
MySQL setup couldn't grant REFERENCES, so deletes had to be done by hand;
the Django models declare a real CASCADE and these tests prove it works.
"""
from django.test import TestCase

from pipeline.models import NonderivTrans, Submission


class ModelTests(TestCase):
    def test_str_returns_accession_number(self):
        """A filing identifies itself by its accession number."""
        sub = Submission(accession_number="0001", created_by="t", source_quarter="2099Q1")
        self.assertEqual(str(sub), "0001")

    def test_cascade_delete_removes_children(self):
        """Deleting a filing takes its transactions with it via the real
        foreign-key CASCADE, no manual cleanup needed."""
        sub = Submission.objects.create(
            accession_number="0001", created_by="t", source_quarter="2099Q1"
        )
        NonderivTrans.objects.create(
            submission=sub, created_by="t", source_quarter="2099Q1"
        )
        sub.delete()
        self.assertEqual(NonderivTrans.objects.count(), 0)
