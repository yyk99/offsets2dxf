"""Generate the body lines of project 89 (sample_data/offset_table.csv)"""

from context import table_of_offsets

import os
import sys
import tempfile
import unittest

import ezdxf

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(source_directory, "tutorial"))


class Test_Project89BodyLines(unittest.TestCase):
    def setUp(self):
        from project89 import Project89

        self.project = Project89()

    def test_body_lines_per_station(self):
        lines = self.project.body_lines()
        self.assertEqual(18, len(lines))
        for station, poly in lines.items():
            heights = [y for _, y in poly]
            self.assertEqual(sorted(heights, reverse=True), heights, station)
        self.assertEqual(13, len(lines["18"]))

    def test_station_18_points(self):
        poly = self.project.body_lines()["18"]
        # the sheer is the top point: 1/2w Deck 4-3-0 at height Sheer 1-7-6
        self.assertEqual((51.0, 19.75), poly[0])
        # the LWL point: breadth 3-9-6, height 0
        self.assertIn((45.75, 0.0), poly)

    def test_generate_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "project89_body.dxf")
            self.project.save_body_lines_as(out)
            doc = ezdxf.readfile(out)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            self.assertEqual(18, len(red))


if __name__ == "__main__":
    unittest.main()
