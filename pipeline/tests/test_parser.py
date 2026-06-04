"""Tests for the SEC archive parser - file reading and ZIP extraction.

Everything runs against temporary files and a patched EXTRACTED_DIR, so
the real data/ directory is never touched.
"""
import json
import os
import tempfile
import zipfile
from unittest import mock

from django.test import SimpleTestCase

from modules import parser


class ReadTsvTests(SimpleTestCase):
    def test_reads_tsv_and_keeps_accession_as_string(self):
        """ACCESSION_NUMBER must stay a string - pandas would otherwise turn
        a leading-zero id into a number and mangle it."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.tsv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("ACCESSION_NUMBER\tTRANS_CODE\n0001234567\tP\n")
            df = parser.read_tsv(path)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "ACCESSION_NUMBER"], "0001234567")

    def test_missing_file_returns_empty(self):
        """A path that doesn't exist yields an empty frame, not an error."""
        self.assertTrue(parser.read_tsv("/no/such/file.tsv").empty)

    def test_empty_file_returns_empty(self):
        """A zero-byte file is treated as no data."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.tsv")
            open(path, "w").close()
            self.assertTrue(parser.read_tsv(path).empty)


class ReadJsonTests(SimpleTestCase):
    def test_reads_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"a": 1}, f)
            self.assertEqual(parser.read_json(path), {"a": 1})

    def test_invalid_json_returns_none(self):
        """Broken metadata shouldn't stop the pipeline - it just returns None."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertIsNone(parser.read_json(path))


class ExtractAndParseTests(SimpleTestCase):
    def test_extract_then_parse_quarter(self):
        """A ZIP with a couple of the relevant TSVs extracts and comes back
        as DataFrames keyed by table name; tables absent from the ZIP show
        up as empty frames rather than missing keys."""
        with tempfile.TemporaryDirectory() as d:
            zip_path = os.path.join(d, "q.zip")
            with zipfile.ZipFile(zip_path, "w") as z:
                z.writestr("SUBMISSION.tsv",
                           "ACCESSION_NUMBER\tISSUERNAME\n0001\tAcme\n")
                z.writestr("NONDERIV_TRANS.tsv",
                           "ACCESSION_NUMBER\tTRANS_CODE\n0001\tP\n")
            extract_dir = os.path.join(d, "extracted")
            with mock.patch.object(parser.config, "EXTRACTED_DIR", extract_dir):
                quarter_dir = parser.extract_zip(zip_path, "2099Q1")
                result = parser.parse_quarter(quarter_dir)

        self.assertEqual(len(result["SUBMISSION"]), 1)
        self.assertEqual(len(result["NONDERIV_TRANS"]), 1)
        self.assertTrue(result["DERIV_TRANS"].empty)
