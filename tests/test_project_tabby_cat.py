"""Tabby Cat: a table of offsets in millimetres, from a lines plan"""

from context import table_of_offsets

import os
import sys
import tempfile
import unittest

import ezdxf

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(source_directory, "tutorial"))

MM = 1.0  # the model works in mm


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

    def test_sheer_line_skips_station_without_sheer_breadth(self):
        """station 1 has no Breadth Sheer (the table): the sheer line starts at
        the station 2, not at the highest point of the station 1 (WL VIII)"""
        lines = self.project.body_lines("raw", "half")
        (sheer,) = self.project.body_sheer_polylines(lines)
        self.assertEqual(11, len(sheer))
        # station 12 is at x = 0, station 2 is the 10th (the bow is station 1)
        self.assertEqual(
            (610, 2155), (round(sheer[-1][0] / MM), round(sheer[-1][1] / MM))
        )
        self.assertEqual(
            (1150, 1610), (round(sheer[0][0] / MM), round(sheer[0][1] / MM))
        )
        # the highest point of the station 1 is not on the sheer line
        (poly,) = lines["1"]
        self.assertNotIn(poly[0], sheer)

    def test_rabbet_line(self):
        """Breadth Rabbet / Height Rabbet of the 12 stations are joined"""
        lines = self.project.body_lines("raw", "half")
        (rabbet,) = self.project.body_rabbet_polylines(lines)
        self.assertEqual(12, len(rabbet))
        points = [(round(x / MM), round(y / MM)) for x, y in rabbet]
        self.assertEqual((40, 900), points[0])  # station 12
        self.assertEqual((35, 930), points[-1])  # station 1
        self.assertIn((85, 515), points)  # station 6

    def test_keel_line(self):
        """Breadth Keel / Height Keel of the 12 stations are joined"""
        lines = self.project.body_lines("raw", "half")
        (keel,) = self.project.body_keel_polylines(lines)
        points = [(round(x / MM), round(y / MM)) for x, y in keel]
        self.assertEqual(12, len(points))
        self.assertEqual((40, 850), points[0])  # station 12
        self.assertEqual((35, 850), points[-1])  # station 1
        self.assertIn((85, 316), points)  # station 6

    def test_diagonals_definition(self):
        """the lines of the diagonals as dimensioned in the construction
        midsection: from 1700 mm above the baseline on the centerline"""
        self.assertEqual(
            {
                "D1": (1700 * MM, 1100 * MM, 0.0),
                "D2": (1700 * MM, 1850 * MM, 1000 * MM),
            },
            self.project.diagonals_positions(),
        )
        self.assertEqual("Diagonal D1", self.project.diagonal_row("D1"))
        # D2 ends on the design waterline
        self.assertAlmostEqual(
            self.project.diagonals_positions()["D2"][2],
            self.project.waterlines_positions()["DWL"],
        )

    def test_diagonal_points(self):
        """the point of a diagonal is on its line, as far from (0, y0) as the
        table says"""
        import math

        for name, (y0, x1, y1) in self.project.diagonals_positions().items():
            row = self.project.diagonal_row(name)
            for station in ("2", "6", "12"):
                distance = self.project.breadth_at(station, row)
                x, y = [
                    (x, y)
                    for x, y, bs, _ in self.project.loft_body_line_sources(
                        station, self.project.body_points()
                    )
                    if bs == row
                ][0]
                self.assertAlmostEqual(distance, math.hypot(x, y - y0), places=6)
                self.assertAlmostEqual((y - y0) * x1, (y1 - y0) * x, places=6)

    def test_diagonals_agree_with_the_table(self):
        """the diagonal points are on the sections made of the other points
        of the table (within 10 mm): the table and the drawn diagonals agree.
        Not at the station 1: its section has no points above WL VIII (no
        sheer breadth)"""
        import math

        def is_diagonal(source):
            return isinstance(source, str) and source.startswith("Diagonal")

        def dist(p, a, b):
            ex, ey = b[0] - a[0], b[1] - a[1]
            t = ((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / (ex * ex + ey * ey)
            t = max(0.0, min(1.0, t))
            return math.hypot(p[0] - a[0] - t * ex, p[1] - a[1] - t * ey)

        for station in [str(n) for n in range(2, 13)]:
            srcs = self.project.loft_body_line_sources(
                station, self.project.body_points()
            )
            others = [(x, y) for x, y, bs, _ in srcs if not is_diagonal(bs)]
            for x, y, bs, _ in srcs:
                if is_diagonal(bs):
                    d = min(dist((x, y), a, b) for a, b in zip(others, others[1:]))
                    self.assertLess(d / MM, 10, (station, bs))

    def test_diagonal_plan_lines(self):
        """the diagonals in the plan view, below the plan centerline (the
        waterlines and the sheer are above it)"""
        lines = self.project.loft_diagonal_plan_lines()
        self.assertEqual(["D1", "D2"], list(lines))
        origin = self.project.grid_y_origins()[1]
        positions = self.project.station_positions()
        for name, poly in lines.items():
            self.assertEqual(12, len(poly))
            self.assertEqual([positions[s] for s in positions], [x for x, _ in poly])
            for _, y in poly:
                self.assertLess(y, origin)
        # station 6, D1: 1190 mm along the line to (1100, 0) from (0, 1700):
        # the half-breadth of the hull point is 1190 * 1100 / 2025
        d1 = dict(lines["D1"])
        self.assertAlmostEqual(
            1190 * 1100 / (1100**2 + 1700**2) ** 0.5,
            (origin - d1[positions["6"]]) / MM,
            places=3,
        )
        # the plan view is drawn in the model file: the red lines include them
        import tempfile
        import ezdxf

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "tabby_cat.dxf")
            self.project.save_model_as(out)
            msp = ezdxf.readfile(out).modelspace()
            texts = [e.dxf.text for e in msp if e.dxftype() == "TEXT"]
            self.assertIn("D1", texts)
            self.assertIn("D2", texts)

    def test_diagonals_in_the_grid(self):
        segments = self.project.diagonal_segments(10.0, both=True)
        self.assertEqual(["D1", "D2"], list(segments))
        (a, b), (c, d) = segments["D1"]
        self.assertEqual((10.0, 1700 * MM), a)
        self.assertAlmostEqual(10.0 + 1100 * MM, b[0])
        self.assertAlmostEqual(0.0, b[1])
        self.assertAlmostEqual(10.0 - 1100 * MM, d[0])  # mirror image

    def test_body_line_station_6(self):
        (poly,) = self.project.body_lines("raw")["6"]
        points = [(round(x / MM), round(y / MM)) for x, y in poly]
        # sheer, 8 waterlines, 4 buttocks, the rabbet (breadth 85 mm) and the
        # keel (316 mm: a straight line between the stations 5 and 10); the
        # dashes of the source
        # the 2 diagonals and the horizontal link from the keel to the
        # centerline
        self.assertEqual(1 + 8 + 4 + 2 + 2 + 1, len(points))
        self.assertEqual((0, 316), points[-1])
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
                e.dxf.text
                for e in ezdxf.readfile(out).modelspace()
                if e.dxftype() == "TEXT"
            ]
            self.assertIn("DWL (1000 mm)", texts)
            self.assertIn("B 4 (1200 mm)", texts)


if __name__ == "__main__":
    unittest.main()
