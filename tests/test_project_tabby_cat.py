"""Tabby Cat: a table of offsets in millimetres, from a lines plan"""

from context import table_of_offsets

import os
import sys
import tempfile
import unittest

import ezdxf

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(source_directory, "tutorial"))

MM = 1.0 / 25.4


class Test_ProjectTabbyCat(unittest.TestCase):
    def setUp(self):
        from project_tabby_cat import ProjectTabbyCat

        self.project = ProjectTabbyCat()

    def test_table_is_as_in_the_source(self):
        too = self.project._too
        self.assertEqual("mm", self.project.offsets_unit())
        self.assertEqual(
            [str(i) for i in range(1, 13)], [c for c in too.columns if c != "#"]
        )
        self.assertEqual("2290", too[too["#"] == "Height Sheer"].iloc[0]["1"])
        self.assertEqual("1488", too[too["#"] == "Breadth WL VIII"].iloc[0]["7"])

    def test_stations(self):
        positions = self.project.station_positions()
        self.assertEqual(12, len(positions))
        self.assertEqual(0, positions["12"])
        self.assertAlmostEqual(510 * 11 * MM, positions["1"])

    def test_waterlines(self):
        wl = self.project.waterlines_positions()
        self.assertEqual(
            ["WL 1", "WL 2", "WL 3", "WL 4", "DWL", "WL 6", "WL 7", "WL 8"], list(wl)
        )
        self.assertEqual(
            [600, 700, 800, 900, 1000, 1150, 1300, 1450],
            [round(h / MM) for h in wl.values()],
        )
        self.assertEqual("Breadth WL V", self.project.waterline_row("DWL"))
        self.assertEqual("Breadth WL VIII", self.project.waterline_row("WL 8"))

    def test_body_line_station_6(self):
        (poly,) = self.project.body_lines("raw")["6"]
        points = [(round(x / MM), round(y / MM)) for x, y in poly]
        # sheer, 8 waterlines, 4 buttocks, the rabbet (breadth 85 mm) and the
        # keel (316 mm: a straight line between the stations 5 and 10); the
        # dashes of the source
        self.assertEqual(1 + 8 + 4 + 2, len(points))
        self.assertIn((85, 515), points)
        self.assertIn((85, 316), points)  # Breadth Keel, Height Keel
        self.assertEqual((1435, 1715), points[0])
        self.assertIn((1245, 1000), points)  # DWL
        for breadth, height in [(300, 578), (600, 670), (900, 785), (1200, 956)]:
            self.assertIn((breadth, height), points)

    def test_generate_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({}, {"body_placement": "right", "body_sides": "split"}):
                out = os.path.join(tmp, "tabby_cat.dxf")
                self.project.save_model_as(out, **kwargs)
                self.assertGreater(len(list(ezdxf.readfile(out).modelspace())), 50)
            out = os.path.join(tmp, "station6.dxf")
            self.project.save_station_as(out, "6")
            texts = [
                e.dxf.text for e in ezdxf.readfile(out).modelspace() if e.dxftype() == "TEXT"
            ]
            self.assertIn("DWL (1000 mm)", texts)
            self.assertIn("B 4 (1200 mm)", texts)


if __name__ == "__main__":
    unittest.main()
