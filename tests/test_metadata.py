import os
import shutil
import tempfile
import unittest

from bztag.core.bztagerror import MetadataError
from bztag.core.metadata import apply_changes, read_tags

_EMPTY_PATH = None


class TaggedFileMixin:
    def _make_mp3(self, name, tagged=False):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as handle:
            handle.write(b"\xff\xfb\x90\x00" + b"\x00" * 128)
        if tagged:
            apply_changes(path, {"title": "Seed Title"})
        return path


class ReadTagsTest(unittest.TestCase, TaggedFileMixin):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_untagged_file_reads_all_none(self):
        path = self._make_mp3("empty.mp3")
        self.assertEqual(
            read_tags(path),
            {key: None for key in (
                "title", "artist", "album", "album_artist",
                "track_number", "disc_number", "year",
                "genre", "composer", "comment",
            )},
        )

    def test_reads_written_values_back(self):
        path = self._make_mp3("plain.mp3", tagged=True)
        self.assertEqual(
            read_tags(path),
            {key: None for key in (
                "artist", "album", "album_artist",
                "track_number", "disc_number", "year",
                "genre", "composer", "comment",
            )} | {"title": "Seed Title"},
        )

    def test_missing_file_raises_metadata_error(self):
        with self.assertRaises(MetadataError):
            read_tags(os.path.join(self.dir, "missing.mp3"))


class ApplyChangesTest(unittest.TestCase, TaggedFileMixin):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_writes_text_keys(self):
        path = self._make_mp3("plain.mp3")
        apply_changes(path, {
            "title": "New Title",
            "artist": "Artist",
            "album": "Album",
            "album_artist": "Album Artist",
            "composer": "Composer",
            "year": "2026",
            "genre": "Rock",
            "comment": "hello",
        })
        read = read_tags(path)
        self.assertEqual(read["title"], "New Title")
        self.assertEqual(read["artist"], "Artist")
        self.assertEqual(read["album"], "Album")
        self.assertEqual(read["album_artist"], "Album Artist")
        self.assertEqual(read["composer"], "Composer")
        self.assertEqual(read["year"], "2026")
        self.assertEqual(read["genre"], "Rock")
        self.assertEqual(read["comment"], "hello")

    def test_writes_numbers_as_strings(self):
        path = self._make_mp3("plain.mp3")
        apply_changes(path, {"disc_number": 2})
        self.assertEqual(read_tags(path)["disc_number"], "2")

    def test_track_written_as_nt_only(self):
        path = self._make_mp3("plain.mp3")
        apply_changes(path, {"track_number": "3/12"})
        self.assertEqual(read_tags(path)["track_number"], "3/12")

    def test_bare_track_number_rejected(self):
        path = self._make_mp3("plain.mp3")
        with self.assertRaises(MetadataError):
            apply_changes(path, {"track_number": "3"})

    def test_unknown_key_rejected(self):
        path = self._make_mp3("plain.mp3", tagged=True)
        with self.assertRaises(MetadataError):
            apply_changes(path, {"bpm": "120"})
        self.assertEqual(read_tags(path)["title"], "Seed Title")

    def test_failed_write_leaves_file_untagged(self):
        path = self._make_mp3("plain.mp3")
        with self.assertRaises(MetadataError):
            apply_changes(path, {"track_number": "9"})
        self.assertIsNone(read_tags(path)["track_number"])


if __name__ == "__main__":
    unittest.main()
