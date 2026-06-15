"""Tests for the SEC downloader - quarter discovery and local lookups.

Network access is mocked and file lookups use a temporary RAW_DIR, so the
tests neither hit SEC nor touch the real data/ directory.
"""
import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from modules import downloader


class ListExistingTests(SimpleTestCase):
    def test_finds_downloaded_zip_ignores_others(self):
        """Only files matching the SEC naming scheme for a target year count;
        anything else in the folder is ignored."""
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "2024q1_form345.zip"), "w").close()
            open(os.path.join(d, "irrelevant.txt"), "w").close()
            with mock.patch.object(downloader.config, "RAW_DIR", d):
                result = downloader.list_existing_quarters()
        self.assertEqual([label for label, _ in result], ["2024Q1"])

    def test_is_already_downloaded(self):
        """The existence check flips once the file is actually present."""
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(downloader.config, "RAW_DIR", d):
                self.assertFalse(downloader.is_already_downloaded("x.zip"))
                open(os.path.join(d, "x.zip"), "w").close()
                self.assertTrue(downloader.is_already_downloaded("x.zip"))


class AvailableQuartersTests(SimpleTestCase):
    def test_scrapes_quarter_links(self):
        """Quarter links are discovered dynamically from the page; relative
        hrefs get the SEC host prepended, absolute ones are kept as-is."""
        html = """
        <html><body>
          <a href="/files/2024q1_form345.zip">2024 Q1</a>
          <a href="https://www.sec.gov/files/2024q2_form345.zip">2024 Q2</a>
          <a href="/files/readme.txt">not a quarter</a>
        </body></html>
        """
        fake = mock.Mock(text=html)
        fake.raise_for_status = mock.Mock()
        with mock.patch.object(downloader.requests, "get", return_value=fake):
            result = downloader.get_available_quarters()

        self.assertEqual(len(result), 2)
        self.assertIn(
            ("2024Q1", "https://www.sec.gov/files/2024q1_form345.zip"), result
        )
        self.assertIn(
            ("2024Q2", "https://www.sec.gov/files/2024q2_form345.zip"), result
        )

    def test_filters_to_requested_years(self):
        """Passing years scopes discovery; quarters outside them are ignored
        (so --year/--years really limits what gets downloaded)."""
        html = """
        <html><body>
          <a href="/files/2023q4_form345.zip">2023 Q4</a>
          <a href="/files/2024q1_form345.zip">2024 Q1</a>
        </body></html>
        """
        fake = mock.Mock(text=html)
        fake.raise_for_status = mock.Mock()
        with mock.patch.object(downloader.requests, "get", return_value=fake):
            result = downloader.get_available_quarters(years=[2024])
        self.assertEqual([label for label, _ in result], ["2024Q1"])


class DownloadRetryTests(SimpleTestCase):
    def test_retries_on_server_error_then_succeeds(self):
        """A 503 triggers a retry; the next, good response is streamed to
        disk. time.sleep is patched out so the backoff doesn't slow the test."""
        bad = mock.Mock(status_code=503)
        good = mock.Mock(status_code=200)
        good.raise_for_status = mock.Mock()
        good.iter_content = mock.Mock(return_value=[b"payload"])

        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(downloader.config, "RAW_DIR", d), \
                 mock.patch.object(downloader.time, "sleep"), \
                 mock.patch.object(downloader.requests, "get",
                                   side_effect=[bad, good]) as get:
                path = downloader.download_quarter("http://x/y.zip", "y.zip",
                                                   max_retries=3)

            # check inside the block - the temp dir is gone once we leave it
            self.assertEqual(get.call_count, 2)
            self.assertTrue(os.path.isfile(path))
