"""The ferrocement hull: a table of offsets in millimetres"""

from context import table_of_offsets

import os
import sys
import tempfile
import unittest

import ezdxf

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(source_directory, "tutorial"))

MM = 1.0 / 25.4


class Test_ProjectFerrocement(unittest.TestCase):
    def setUp(self):
        from project_ferrocement import ProjectFerrocement

        self.project = ProjectFerrocement()

    def test_unit(self):
        self.assertEqual("mm", self.project.offsets_unit())

    def test_table_is_as_in_the_source(self):
        # the cells are the numbers from the source, in millimetres
        too = self.project._too
        self.assertEqual(
            ["T"] + [str(i) for i in range(1, 13)], [c for c in too.columns if c != "#"]
        )
        row = too[too["#"] == "Height Sheer"].iloc[0]
        self.assertEqual("2644", row["9"])
        row = too[too["#"] == "Breadth WL 5"].iloc[0]
        self.assertEqual("1290", row["2"])

    def test_inches(self):
        self.assertAlmostEqual(2644 * MM, self.project.height_at("9", "Height Sheer"))
        self.assertAlmostEqual(
            1290 * MM, self.project.breadth_at("2", "Breadth WL 5")
        )
        with self.assertRaises(ValueError):
            self.project.breadth_at("T", "Breadth WL 8")  # a dash in the source

    def test_stations(self):
        positions = self.project.station_positions()
        self.assertEqual(13, len(positions))
        self.assertEqual(0, positions["T"])
        self.assertAlmostEqual(1000 * MM, positions["1"])
        self.assertAlmostEqual(12000 * MM, positions["12"])

    def test_waterlines(self):
        # the draught is 1800 mm: the design waterline, WL 5, is at 1800 mm;
        # the waterlines are 250 mm apart
        wl = self.project.waterlines_positions()
        self.assertEqual(
            ["WL 1", "WL 2", "WL 3", "WL 4", "DWL", "WL 6", "WL 7", "WL 8"], list(wl)
        )
        self.assertAlmostEqual(1800 * MM, wl["DWL"])
        self.assertAlmostEqual(800 * MM, wl["WL 1"])
        self.assertAlmostEqual(2550 * MM, wl["WL 8"])
        heights = list(wl.values())
        for lower, upper in zip(heights, heights[1:]):
            self.assertAlmostEqual(250 * MM, upper - lower)

    def test_body_lines_with_waterlines(self):
        without = self.project.body_lines("raw")["6"][0]
        with_wl = self.project.body_lines("raw", waterlines=True)["6"][0]
        self.assertEqual(len(without) + 8, len(with_wl))
        # WL 5 at station 6: breadth 1480 mm at the draught
        self.assertIn(
            (round(1480 * MM, 6), round(1800 * MM, 6)),
            [(round(x, 6), round(y, 6)) for x, y in with_wl],
        )

    def test_body_lines(self):
        lines = self.project.body_lines("raw")
        self.assertEqual(13, len(lines))
        (poly,) = lines["6"]
        # the sheer is the top point
        self.assertAlmostEqual(1562 * MM, poly[0][0])
        self.assertAlmostEqual(2406 * MM, poly[0][1])
        heights = [y for _, y in poly]
        self.assertEqual(sorted(heights, reverse=True), heights)
        # the buttocks are in the section: 500, 1000 and 1500 mm
        xs = [round(x / MM) for x, _ in poly]
        for buttock in (500, 1000, 1500):
            self.assertIn(buttock, xs)

    def test_generate_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({}, {"body_placement": "right", "body_sides": "split"}):
                out = os.path.join(tmp, "ferrocement.dxf")
                self.project.save_model_as(out, **kwargs)
                doc = ezdxf.readfile(out)
                self.assertGreater(len(list(doc.modelspace())), 50)
            out = os.path.join(tmp, "body.dxf")
            self.project.save_body_lines_as(out)
            doc = ezdxf.readfile(out)
            # the default is split: one polyline per station, two for the
            # midship station
            self.assertEqual(14, len([e for e in doc.modelspace()]))


if __name__ == "__main__":
    unittest.main()
