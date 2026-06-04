"""Tests for the data preparation transforms.

These exercise the pure pandas logic - column cleaning, SEC date
parsing, the reporting-owner merge with its OR-combined role flags, and
the metadata stamping - without ever touching the database.
"""
import pandas as pd
from django.test import SimpleTestCase

from modules import data_preparation as prep


class CleanColumnsTests(SimpleTestCase):
    """_clean_columns normalises the messy headers SEC ships."""

    def test_lowercases_and_strips(self):
        """SEC headers arrive in mixed case with stray whitespace; the rest
        of the pipeline relies on them being lowercase and trimmed."""
        df = pd.DataFrame(columns=["  ACCESSION_NUMBER ", "Trans_Date"])
        cleaned = prep._clean_columns(df)
        self.assertEqual(list(cleaned.columns), ["accession_number", "trans_date"])


class ParseDateTests(SimpleTestCase):
    """_parse_date turns the DD-MON-YYYY SEC format into real dates."""

    def test_parses_sec_format_and_coerces_garbage(self):
        """Valid SEC dates parse; anything unparseable becomes NaT instead
        of raising, so one bad cell can't abort a whole quarter."""
        parsed = prep._parse_date(pd.Series(["15-JAN-2025", "garbage"]))
        self.assertEqual(parsed.iloc[0], pd.Timestamp("2025-01-15"))
        self.assertTrue(pd.isna(parsed.iloc[1]))


class PrepareSubmissionsTests(SimpleTestCase):
    """prepare_submissions merges owners into filings and derives flags."""

    def _owner_df(self):
        """Two owners on filing 0001, one on 0002 - covers the OR-combine."""
        return pd.DataFrame({
            "ACCESSION_NUMBER": ["0001", "0001", "0002"],
            "RPTOWNERCIK": [111, 222, 333],
            "RPTOWNERNAME": ["Alice", "Bob", "Carol"],
            "RPTOWNER_TITLE": ["CEO", "CFO", None],
            "RPTOWNER_RELATIONSHIP": ["Director", "Officer", "TenPercentOwner"],
        })

    def _sub_df(self):
        """Two filings with the SEC issuer column names that get renamed."""
        return pd.DataFrame({
            "ACCESSION_NUMBER": ["0001", "0002"],
            "FILING_DATE": ["15-JAN-2025", "20-FEB-2025"],
            "ISSUERCIK": [900, 901],
            "ISSUERNAME": ["Acme", "Globex"],
            "ISSUERTRADINGSYMBOL": ["ACM", "GLX"],
        })

    def test_merges_owner_and_or_combines_flags(self):
        """Filing 0001 has a Director and an Officer, so both flags must be
        set; the first owner's CIK wins, and issuer columns get renamed."""
        result = prep.prepare_submissions(
            self._sub_df(), self._owner_df(), "2025Q1"
        ).set_index("accession_number")

        self.assertEqual(result.loc["0001", "is_director"], 1)
        self.assertEqual(result.loc["0001", "is_officer"], 1)
        self.assertEqual(result.loc["0001", "rptowner_cik"], 111)
        self.assertEqual(result.loc["0002", "is_ten_percent"], 1)
        self.assertEqual(result.loc["0001", "issuer_ticker"], "ACM")
        self.assertEqual(result.loc["0001", "filing_date"], pd.Timestamp("2025-01-15"))

    def test_metadata_is_stamped(self):
        """Every prepared row carries the source quarter for idempotent
        delete-then-insert later on."""
        result = prep.prepare_submissions(self._sub_df(), self._owner_df(), "2025Q1")
        self.assertTrue((result["source_quarter"] == "2025Q1").all())


class PrepareTransactionsTests(SimpleTestCase):
    """prepare_transactions cleans types and computes nominal volume."""

    def _raw(self):
        return pd.DataFrame({
            "ACCESSION_NUMBER": ["0001", "0002"],
            "TRANS_DATE": ["15-JAN-2025", "bad-date"],
            "TRANS_CODE": ["P", "S"],
            "TRANS_SHARES": ["100", "200"],
            "TRANS_PRICEPERSHARE": ["10", "5"],
        })

    def test_renames_and_computes_nominal_volume(self):
        """shares * price gives nominal volume, and the SEC column names
        are mapped onto the DB schema (shares, price_per_share)."""
        result = prep.prepare_transactions(self._raw(), "2025Q1").set_index("accession_number")
        self.assertEqual(result.loc["0001", "shares"], 100)
        self.assertEqual(result.loc["0001", "price_per_share"], 10)
        self.assertEqual(result.loc["0001", "nominal_volume"], 1000)

    def test_unparseable_date_becomes_nat(self):
        """A broken date is coerced to NaT rather than blowing up."""
        result = prep.prepare_transactions(self._raw(), "2025Q1").set_index("accession_number")
        self.assertTrue(pd.isna(result.loc["0002", "trans_date"]))

    def test_empty_input_returns_empty(self):
        """A table with headers but no rows passes straight through as empty
        instead of being processed further."""
        raw = pd.DataFrame(columns=["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE"])
        result = prep.prepare_transactions(raw, "2025Q1")
        self.assertTrue(result.empty)

    def test_columnless_empty_input_returns_empty(self):
        """A completely empty frame with no columns - what read_tsv returns
        for a missing file - must not crash on the column cleaning step."""
        result = prep.prepare_transactions(pd.DataFrame(), "2025Q1")
        self.assertTrue(result.empty)
        result = prep.prepare_holdings(pd.DataFrame(), "2025Q1")
        self.assertTrue(result.empty)
