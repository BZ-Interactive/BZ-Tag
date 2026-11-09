import io
import contextlib
import os
import shutil
import tempfile
import unittest

from bztag.cli import collect_edits, main
import argparse


def _namespace(**attrs):
    defaults = dict(
        directory=".", tui=False, cli=False, all=False, auto_number=False,
        rename=None, dry_run=False, title=None, artist=None, album=None,
        album_artist=None, composer=None, track_number=None, disc_number=None,
        year=None, genre=None, comment=None, art=None,
    )
    defaults.update(attrs)
    return argparse.Namespace(**defaults)


class CollectEditsTest(unittest.TestCase):
    def test_only_supplied_flags_map_into_dict(self):
        args = _namespace(album="X", year=2026)
        self.assertEqual(collect_edits(args), {"album": "X", "year": 2026})

    def test_no_flags_gives_empty_dict(self):
        self.assertEqual(collect_edits(_namespace()), {})


class MainFlowTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.mp3s = []
        for name in ("01.a.mp3", "02.b.mp3", "03.c.mp3"):
            path = os.path.join(self.dir, name)
            with open(path, "wb") as handle:
                handle.write(b"\xff\xfb\x90\x00" + b"\x00" * 128)
            self.mp3s.append(path)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = 0
            try:
                main(argv)
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
            return code, out.getvalue(), err.getvalue()

    def test_zero_args_reports_tui_mode(self):
        code, out, _ = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("TUI", out)

    def test_mp3_without_edits_is_argparse_error(self):
        code, _, err = self._run([self.mp3s[0]])
        self.assertEqual(code, 2)
        self.assertIn("no changes specified", err)

    def test_directory_without_all_is_argparse_error(self):
        code, _, err = self._run([self.dir, "--set-album", "X"])
        self.assertEqual(code, 2)
        self.assertIn("requires --all", err)

    def test_all_without_edits_is_argparse_error(self):
        code, _, err = self._run([self.dir, "--all"])
        self.assertEqual(code, 2)
        self.assertIn("no changes specified", err)

    def test_missing_target_is_argparse_error(self):
        code, _, err = self._run([os.path.join(self.dir, "nope"), "--all",
                                  "--set-album", "X"])
        self.assertEqual(code, 2)
        self.assertIn("no such MP3 file or directory", err)

    def test_dry_run_reports_without_writing(self):
        code, out, _ = self._run([self.dir, "--all", "--set-album", "X",
                                  "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("(dry-run)", out)
        self.assertIn("3 found, 3 changed", out)
        from bztag.core.metadata import read_tags
        self.assertIsNone(read_tags(self.mp3s[0])["album"])

    def test_real_apply_writes_album(self):
        code, out, _ = self._run([self.dir, "--all", "--set-album", "X"])
        self.assertEqual(code, 0)
        self.assertIn("3 found, 3 changed, 0 skipped, 0 failed", out)
        from bztag.core.metadata import read_tags
        self.assertEqual(read_tags(self.mp3s[0])["album"], "X")

    def test_track_number_composes_nt_from_directory_count(self):
        code, _, _ = self._run([self.mp3s[1], "--set-track-number", "2"])
        self.assertEqual(code, 0)
        from bztag.core.metadata import read_tags
        self.assertEqual(read_tags(self.mp3s[1])["track_number"], "2/3")

    def test_unimplemented_flags_get_clear_error(self):
        code, _, err = self._run([self.dir, "--all", "--set-album", "X",
                                  "--auto-number"])
        self.assertEqual(code, 2)
        self.assertIn("not implemented yet: --auto-number", err)


if __name__ == "__main__":
    unittest.main()
