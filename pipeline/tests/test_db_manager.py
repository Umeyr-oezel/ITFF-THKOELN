"""Tests for the idempotent import layer.

These run against the database because the behaviour under test - the
delete-then-insert idempotency, the never-deleted audit log, and the
foreign-key orphan handling - only exists at the DB boundary.
"""
import pandas as pd
from django.test import TestCase

from modules import db_manager
from pipeline.models import NonderivTrans, PipelineLog, Submission


def _prepared(accessions, trans_accessions):
    """Build a minimal prepared-quarter dict the importer accepts.

    Only submissions and nonderiv_trans carry rows; the other three child
    tables are empty, which the importer skips. trans_accessions can point
    at a missing filing to exercise the orphan drop.
    """
    sub = pd.DataFrame({
        "accession_number": accessions,
        "filing_date": [pd.Timestamp("2099-01-01")] * len(accessions),
        "created_by": ["test"] * len(accessions),
        "source_quarter": ["2099Q1"] * len(accessions),
    })
    trans = pd.DataFrame({
        "accession_number": trans_accessions,
        "trans_date": [pd.Timestamp("2099-01-02")] * len(trans_accessions),
        "trans_code": ["P"] * len(trans_accessions),
        "shares": [10] * len(trans_accessions),
        "price_per_share": [5] * len(trans_accessions),
        "created_by": ["test"] * len(trans_accessions),
        "source_quarter": ["2099Q1"] * len(trans_accessions),
    })
    empty = pd.DataFrame()
    return {
        "submissions": sub,
        "nonderiv_trans": trans,
        "nonderiv_holdings": empty,
        "deriv_trans": empty,
        "deriv_holdings": empty,
    }


class ImportIdempotencyTests(TestCase):
    def test_reimport_does_not_duplicate(self):
        """Importing the same quarter twice must leave the same row counts -
        that's the whole point of delete-then-insert."""
        prepared = _prepared(["0001", "0002"], ["0001", "0002"])
        db_manager.import_quarter(prepared, "2099Q1")
        db_manager.import_quarter(prepared, "2099Q1")
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(NonderivTrans.objects.count(), 2)

    def test_pipeline_log_accumulates_across_runs(self):
        """pipeline_log is an audit trail: two runs leave two rows, it is
        never wiped on re-import."""
        prepared = _prepared(["0001"], ["0001"])
        db_manager.import_quarter(prepared, "2099Q1")
        db_manager.import_quarter(prepared, "2099Q1")
        self.assertEqual(PipelineLog.objects.count(), 2)

    def test_orphan_transactions_are_dropped(self):
        """A transaction whose filing isn't in this quarter's submissions is
        dropped before insert rather than failing the whole batch."""
        prepared = _prepared(["0001"], ["0001", "MISSING"])
        db_manager.import_quarter(prepared, "2099Q1")
        self.assertEqual(NonderivTrans.objects.count(), 1)
