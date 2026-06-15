"""Tests for the evaluation ranking helper.

top_n_by reproduces the old SQL `ORDER BY <metric> DESC LIMIT N`: it
returns the N highest rows, pushes NULL aggregates to the bottom (so a
missing value never outranks a real one), and never exceeds config.TOP_N.
This is the pandas side of the query refactor, so it runs without a
database.
"""
import pandas as pd
from django.test import SimpleTestCase

import config
from modules import evaluation


class TopNByTests(SimpleTestCase):
    def _frame(self):
        """Six issuers, one with a NULL metric - more rows than the Top-5."""
        return pd.DataFrame({
            "issuer_cik": [1, 2, 3, 4, 5, 6],
            "total_volume": [50, 10, None, 30, 20, 40],
        })

    def test_returns_highest_first_capped_at_top_n(self):
        """Rows come back sorted high-to-low and capped at TOP_N."""
        out = evaluation.top_n_by(self._frame(), "total_volume")
        self.assertEqual(len(out), config.TOP_N)
        self.assertEqual(list(out["total_volume"])[:3], [50, 40, 30])

    def test_nulls_sort_last(self):
        """A NULL aggregate is the row left out, never a real value."""
        out = evaluation.top_n_by(self._frame(), "total_volume")
        self.assertFalse(out["total_volume"].isna().any())

    def test_empty_frame_passes_through(self):
        """An empty input returns empty instead of raising."""
        self.assertTrue(
            evaluation.top_n_by(pd.DataFrame(), "total_volume").empty
        )
