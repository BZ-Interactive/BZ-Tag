import os
import shutil
import tempfile
import unittest

from bztag.core.bztagerror import ScanError
from bztag.core.scanner import scan


class ScannerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def _touch(self, name, content=b""):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as handle:
            handle.write(content)
        return path

    def test_discovers_mp3_files_only(self):
        self._touch("b.MP3")
        self._touch("a.mp3")
        self._touch("c.wav")
        self._touch("d.txt")
        self.assertEqual(
            scan(self.dir),
            [
                os.path.join(self.dir, "a.mp3"),
                os.path.join(self.dir, "b.MP3"),
            ],
        )

    def test_is_non_recursive(self):
        self._touch("a.mp3")
        os.mkdir(os.path.join(self.dir, "inner"))
        self._touch(os.path.join("inner", "nested.mp3"))
        self.assertEqual(scan(self.dir), [os.path.join(self.dir, "a.mp3")])

    def test_sorts_case_insensitively(self):
        self._touch("B.mp3")
        self._touch("a.mp3")
        self.assertEqual(
            scan(self.dir),
            [
                os.path.join(self.dir, "a.mp3"),
                os.path.join(self.dir, "B.mp3"),
            ],
        )

    def test_excludes_directory_named_like_mp3(self):
        os.mkdir(os.path.join(self.dir, "dir.mp3"))
        self.assertEqual(scan(self.dir), [])

    def test_join_keeps_given_directory_prefix(self):
        self._touch("a.mp3")
        self.assertEqual(scan(self.dir), [os.path.join(self.dir, "a.mp3")])

    def test_empty_dir_returns_empty_list(self):
        self.assertEqual(scan(self.dir), [])

    def test_missing_directory_raises_scan_error(self):
        with self.assertRaises(ScanError):
            scan(os.path.join(self.dir, "does-not-exist"))


if __name__ == "__main__":
    unittest.main()
