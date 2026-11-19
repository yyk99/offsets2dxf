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
        lines = self.project.body_lines("max_breadth", "half")
        self.assertEqual(
            ["1", "2", "3", "4", "5", "6", "7", "8", "TRAN."], list(lines.keys())
        )
        for station, polys in lines.items():
            (poly,) = polys
            self.assertGreater(len(poly), 2, station)
            heights = [y for _, y in poly]
            self.assertEqual(sorted(heights, reverse=True), heights, station)

    def test_default_is_split(self):
        # in the middle of the profile view the default is "split"
        default = self.project.body_lines()
        self.assertEqual(default, self.project.body_lines("max_breadth", "split"))
        self.assertEqual(
            [1] * 8 + [2], sorted(len(polys) for polys in default.values())
        )

    def test_station_5_sheer_point(self):
        (poly,) = self.project.body_lines("raw")["5"]
        # SHEER breadth 4-4-0 == 52.0; LWL to SHEER 2-0-3 + LWL above base 4-1-7
        top = poly[0]
        self.assertEqual(52.0, top[0])
        self.assertEqual(
            table_of_offsets.TableOfOffsets.offset2double("2-0-3")
            + self.project._y_lwl,
            top[1],
        )

    def test_both_sides(self):
        half = self.project.body_lines("raw")
        both = self.project.body_lines("raw", "both")
        for station, polys in both.items():
            (poly,) = polys
            (right,) = half[station]
            # the right half down to the keel, then the mirrored left half up
            self.assertGreaterEqual(len(poly), 2 * len(right) - 1, station)
            self.assertEqual(right[0], poly[0], station)
            self.assertEqual((-right[0][0], right[0][1]), poly[-1], station)
            # symmetric about the centerline
            self.assertEqual({(-x, y) for x, y in poly}, set(poly), station)

    def test_generate_dxf(self):
        """Generate the body lines, both sides of every station, as a DXF"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "blue_moon_body.dxf")
            self.project.save_body_lines_as(out, "raw", "both")
            self.assertTrue(os.path.exists(out))
            doc = ezdxf.readfile(out)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            # one polyline per station, the sheer, rabbet and keel lines of each
            # side
            self.assertEqual(9 + 2 + 2 + 2, len(red))
            # the drawing is symmetric about the centerline x = 0
            xs = [p[0] for e in red for p in e.points()]
            self.assertAlmostEqual(max(xs), -min(xs))
            self.assertLess(min(xs), 0)

    def test_generate_dxf_split_on_the_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "blue_moon_split.dxf")
            self.project.save_model_as(out, body_placement="right", body_sides="split")
            doc = ezdxf.readfile(out)
            self.assertGreater(len(list(doc.modelspace())), 50)


if __name__ == "__main__":
    unittest.main()
