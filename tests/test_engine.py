import os
import shutil
import tempfile
import unittest

from bztag.core.bztagerror import ScanError, SorterError
from bztag.core.metadata import read_tags
from bztag.engine import Engine, Status

MP3_BYTES = b"\xff\xfb\x90\x00" + b"\x00" * 128


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.mp3s = []
        for name in ("01.a.mp3", "02.b.mp3", "03.c.mp3"):
            path = os.path.join(self.dir, name)
            with open(path, "wb") as handle:
                handle.write(MP3_BYTES)
            self.mp3s.append(path)
        self.engine = Engine(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_files_returns_sorted_copy(self):
        listing = self.engine.files()
        self.assertEqual(listing, self.mp3s)
        listing.append("sneaky")
        self.assertEqual(len(self.engine.files()), 3)

    def test_files_with_sort_how_sorts_copy_only(self):
        self.assertEqual(self.engine.files(sort_how="filename"), self.mp3s)
        self.assertEqual(len(self.engine.files()), 3)
        with self.assertRaises(SorterError):
            self.engine.files(sort_how="track_number")

    def test_bad_target_raises_scan_error(self):
        with self.assertRaises(ScanError):
            Engine(os.path.join(self.dir, "does-not-exist"))

    def test_select_unknown_path_raises(self):
        with self.assertRaises(ScanError):
            self.engine.select([os.path.join(self.dir, "zzz.mp3")])

    def test_selected_follows_inventory_order_not_selection_order(self):
        self.engine.select([self.mp3s[2], self.mp3s[0]])
        self.assertEqual(self.engine.selected(), self.mp3s[:1] + [self.mp3s[2]])

    def test_apply_with_no_selection_is_noop(self):
        self.assertEqual(self.engine.apply({"album": "X"}), [])

    def test_dry_run_reports_without_writing(self):
        self.engine.select_all()
        results = self.engine.apply({"album": "X"}, dry=True)
        self.assertEqual([r.status for r in results],
                         [Status.CHANGED] * 3)
        self.assertIn("-> 'X'", results[0].message)
        self.assertIsNone(read_tags(self.mp3s[0])["album"])

    def test_apply_writes_and_reapply_skips(self):
        self.engine.select_all()
        self.engine.apply({"album": "X"})
        self.assertEqual(read_tags(self.mp3s[0])["album"], "X")
        again = self.engine.apply({"album": "X"})
        self.assertEqual([r.status for r in again], [Status.SKIPPED] * 3)
        self.assertIn("no changes needed", again[0].message)

    def test_disc_number_written_bare(self):
        self.engine.select_all()
        self.engine.apply({"disc_number": 2})
        self.assertEqual(read_tags(self.mp3s[0])["disc_number"], "2")

    def test_single_file_target_deduces_total_from_parent(self):
        single = Engine(self.mp3s[1])
        self.assertEqual(single.files(), [self.mp3s[1]])
        single.select_all()
        results = single.apply({"track_number": 2}, dry=True)
        self.assertEqual(results[0].status, Status.CHANGED)
        self.assertIn("-> '2/3'", results[0].message)

    def test_failing_file_does_not_stop_batch(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root ignores file permissions")
        os.chmod(self.mp3s[0], 0o000)
        try:
            self.engine.select_all()
            results = self.engine.apply({"album": "X"})
            self.assertEqual(results[0].status, Status.FAILED)
            self.assertEqual([r.status for r in results[1:]],
                             [Status.CHANGED] * 2)
            self.assertEqual(read_tags(self.mp3s[1])["album"], "X")
        finally:
            os.chmod(self.mp3s[0], 0o644)


if __name__ == "__main__":
    unittest.main()
