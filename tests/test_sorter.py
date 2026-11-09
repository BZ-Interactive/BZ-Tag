import unittest

from bztag.core.bztagerror import SorterError
from bztag.core.sorter import sort


class FilenameSortTest(unittest.TestCase):
    def test_case_insensitive_order(self):
        self.assertEqual(sort(["B.mp3", "a.mp3"]), ["a.mp3", "B.mp3"])

    def test_filename_order_not_natural_sort(self):
        self.assertEqual(sort(["10.mp3", "02.mp3"]), ["02.mp3", "10.mp3"])

    def test_default_style_is_filename(self):
        self.assertEqual(sort(["b", "a"]), ["a", "b"])

    def test_returns_new_list(self):
        names = ["b", "a"]
        result = sort(names)
        self.assertEqual(names, ["b", "a"])
        self.assertEqual(result, ["a", "b"])

    def test_unknown_style_raises(self):
        with self.assertRaises(SorterError):
            sort(["a.mp3"], how="bogus")


class TrackNumberSkeletonTest(unittest.TestCase):
    def test_skeleton_raises_until_metadata_exists(self):
        with self.assertRaises(SorterError):
            sort(["1.mp3"], how="track_number")


if __name__ == "__main__":
    unittest.main()
