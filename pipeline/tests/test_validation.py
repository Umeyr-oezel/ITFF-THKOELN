"""Tests for the individual plausibility checks.

Each check works on a prepared DataFrame: it flips is_valid to 0 and
appends a flag string for the rows it considers bad. Every test feeds a
mix of good and bad rows and asserts that only the bad ones get flagged -
covering all four mandatory checks plus the four bonus checks.
"""
from datetime import date

import pandas as pd
from django.test import SimpleTestCase

from modules import validation


def _frame(rows):
    """Build a check-ready frame with is_valid/flags pre-initialised.

    The real validation code seeds these two columns before running any
    check, so the tests mirror that starting state.
    """
    df = pd.DataFrame(rows)
    df["is_valid"] = 1
    df["flags"] = ""
    return df


class MandatoryFieldTests(SimpleTestCase):
    def test_flags_missing_accession_or_date(self):
        """accession_number and trans_date are mandatory; a NULL in either
        invalidates the row."""
        df = _frame({
            "accession_number": ["0001", None],
            "trans_date": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-01")],
        })
        out = validation._check_mandatory_fields(df)
        self.assertEqual(out.loc[0, "is_valid"], 1)
        self.assertEqual(out.loc[1, "is_valid"], 0)
        self.assertIn("MISSING_MANDATORY", out.loc[1, "flags"])


class NegativeValueTests(SimpleTestCase):
    def test_negative_price_flagged_but_nan_ignored(self):
        """A negative price is invalid; a missing price is left alone."""
        df = _frame({"price_per_share": [10.0, -5.0, None]})
        out = validation._check_no_negative_prices(df)
        self.assertEqual(list(out["is_valid"]), [1, 0, 1])
        self.assertIn("NEGATIVE_PRICE", out.loc[1, "flags"])

    def test_negative_shares_flagged(self):
        """Same rule for shares - they can't go below zero."""
        df = _frame({"shares": [100.0, -1.0]})
        out = validation._check_no_negative_shares(df)
        self.assertEqual(list(out["is_valid"]), [1, 0])
        self.assertIn("NEGATIVE_SHARES", out.loc[1, "flags"])


class DateLogicTests(SimpleTestCase):
    def test_transaction_after_filing_flagged(self):
        """A transaction dated after its filing is impossible."""
        df = _frame({
            "trans_date": [pd.Timestamp("2025-01-10"), pd.Timestamp("2025-02-10")],
            "filing_date": [pd.Timestamp("2025-01-15"), pd.Timestamp("2025-01-15")],
        })
        out = validation._check_date_logic(df)
        self.assertEqual(out.loc[0, "is_valid"], 1)
        self.assertEqual(out.loc[1, "is_valid"], 0)
        self.assertIn("DATE_AFTER_FILING", out.loc[1, "flags"])


class TransCodeTests(SimpleTestCase):
    def test_unknown_code_flagged(self):
        """Codes outside the documented SEC set are flagged; NULL is fine."""
        df = _frame({"trans_code": ["P", "ZZZ", None]})
        out = validation._check_valid_trans_code(df)
        self.assertEqual(list(out["is_valid"]), [1, 0, 1])
        self.assertIn("UNKNOWN_TRANS_CODE", out.loc[1, "flags"])


class FutureDateTests(SimpleTestCase):
    def test_future_date_flagged(self):
        """A transaction dated after today is almost certainly a data error."""
        future = pd.Timestamp(date.today()) + pd.Timedelta(days=30)
        df = _frame({"trans_date": [pd.Timestamp("2020-01-01"), future]})
        out = validation._check_future_date(df)
        self.assertEqual(out.loc[0, "is_valid"], 1)
        self.assertEqual(out.loc[1, "is_valid"], 0)
        self.assertIn("FUTURE_DATE", out.loc[1, "flags"])


class ReasonablePriceTests(SimpleTestCase):
    def test_price_at_or_above_cap_flagged(self):
        """The cap is inclusive: exactly $1M per share is already suspicious."""
        df = _frame({"price_per_share": [999_999.0, 1_000_000.0]})
        out = validation._check_reasonable_price(df)
        self.assertEqual(out.loc[0, "is_valid"], 1)
        self.assertEqual(out.loc[1, "is_valid"], 0)
        self.assertIn("UNREASONABLE_PRICE", out.loc[1, "flags"])


class OrphanRecordTests(SimpleTestCase):
    def test_missing_submission_flagged(self):
        """Rows whose filing is absent are flagged as orphans (the safety
        net behind the real foreign key)."""
        df = _frame({"_has_submission": [1, 0], "accession_number": ["A", "B"]})
        out = validation._check_orphan_records(df)
        self.assertEqual(out.loc[0, "is_valid"], 1)
        self.assertEqual(out.loc[1, "is_valid"], 0)
        self.assertIn("ORPHAN_RECORD", out.loc[1, "flags"])
