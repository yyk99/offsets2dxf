"""Generate the body lines of the Blue Moon project"""

from context import table_of_offsets

import os
import sys
import tempfile
import unittest

import ezdxf

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
tutorial_directory = os.path.join(source_directory, "tutorial")
sys.path.insert(0, tutorial_directory)

CSV = os.path.join(source_directory, "sample_data_too", "offset_table_blue_moon.csv")


@unittest.skipUnless(os.path.exists(CSV), "submodule sample_data_too is missing")
class Test_BlueMoonBodyLines(unittest.TestCase):
    def setUp(self):
        from projectbluemoon import ProjectBlueMoon

        self.project = ProjectBlueMoon()

    def test_body_lines_per_station(self):
        lines = self.project.body_lines()
        self.assertEqual(
            ["1", "2", "3", "4", "5", "6", "7", "8", "TRAN."], list(lines.keys())
        )
        for station, poly in lines.items():
            self.assertGreater(len(poly), 2, station)
            heights = [y for _, y in poly]
            self.assertEqual(sorted(heights, reverse=True), heights, station)

    def test_station_5_sheer_point(self):
        poly = self.project.body_lines()["5"]
        # SHEER breadth 4-4-0 == 52.0; LWL to SHEER 2-0-3 + LWL above base 4-1-7
        top = poly[0]
        self.assertEqual(52.0, top[0])
        self.assertEqual(
            table_of_offsets.TableOfOffsets.offset2double("2-0-3")
            + self.project._y_lwl,
            top[1],
        )

    def test_generate_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "blue_moon_body.dxf")
            with table_of_offsets.DXF(out) as dxf:
                for poly in self.project.body_lines().values():
                    dxf.add_red_polyline(poly)
            self.assertTrue(os.path.exists(out))
            doc = ezdxf.readfile(out)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            self.assertEqual(9, len(red))


if __name__ == "__main__":
    unittest.main()
