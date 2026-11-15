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
        """the waterlines are in the list of the body line points"""
        (poly,) = self.project.body_lines("raw")["6"]
        # sheer, deck, knuckle, keel, 3 buttocks and 8 waterlines, and the
        # link from the keel to the centerline
        self.assertEqual(4 + 3 + 8 + 1, len(poly))
        # WL 5 at station 6: breadth 1480 mm at the draught
        self.assertIn(
            (round(1480 * MM, 6), round(1800 * MM, 6)),
            [(round(x, 6), round(y, 6)) for x, y in poly],
        )

    def test_body_lines(self):
        lines = self.project.body_lines("raw")
        self.assertEqual(13, len(lines))
        (poly,) = lines["6"]
        points = [(round(x / MM), round(y / MM)) for x, y in poly]
        # the sheer is in the section: breadth 1562 mm, height 2406 mm
        self.assertIn((1562, 2406), points)
        # the highest point is WL 8 (2550 mm), which is above the sheer here
        self.assertEqual((1562, 2550), points[0])
        heights = [y for _, y in poly]
        self.assertEqual(sorted(heights, reverse=True), heights)
        # the buttocks are in the section: 500, 1000 and 1500 mm
        xs = [round(x / MM) for x, _ in poly]
        for buttock in (500, 1000, 1500):
            self.assertIn(buttock, xs)

    def test_annotated_station(self):
        """one station, every point labelled with the sources of its coordinates"""
        points = self.project.loft_body_line_sources("6", self.project.body_points())
        self.assertEqual(15, len(points))
        # from the top down
        heights = [y for _, y, _, _ in points]
        self.assertEqual(sorted(heights, reverse=True), heights)
        sources = [(b, h if isinstance(h, str) else "WL") for _, _, b, h in points]
        self.assertIn(("Breadth Deck", "Height Deck"), sources)
        self.assertIn(("Breadth WL 3", "WL"), sources)
        self.assertIn((500 * MM, "Height Buttock I"), [(b, h) for _, _, b, h in points])

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "station6.dxf")
            self.project.save_station_as(out, "6")
            doc = ezdxf.readfile(out)
            texts = [e.dxf.text for e in doc.modelspace() if e.dxftype() == "TEXT"]
            self.assertIn("station 6", texts)
            self.assertIn("5 (Breadth Deck, Height Deck)", texts)
            self.assertIn("14 (500 mm, Height Buttock I)", texts)
            self.assertIn("9 (Breadth WL 3, 1300 mm)", texts)
            # the base line and the waterlines are named
            self.assertIn("baseline (0 mm)", texts)
            self.assertIn("DWL (1800 mm)", texts)
            self.assertIn("WL 1 (800 mm)", texts)
            # the buttocks are named: 500 mm apart
            self.assertIn("B I (500 mm)", texts)
            self.assertIn("B II (1000 mm)", texts)
            self.assertIn("B III (1500 mm)", texts)
            # the title, 15 points, the base line, 8 waterlines and 3 buttocks
            self.assertEqual(1 + 15 + 1 + 8 + 3, len(texts))
            # horizontal lines: the base line and the 8 waterlines
            ys = sorted(
                round(pts[0][1], 6)
                for pts in (
                    [tuple(p)[:2] for p in e.points()]
                    for e in doc.modelspace()
                    if e.dxf.layer == "grid" and e.dxftype() == "POLYLINE"
                )
                if pts[0][1] == pts[1][1]
            )
            # (the file is in millimetres, the model in inches)
            expected = [0.0] + [
                round(h / MM, 6) for h in self.project.waterlines_positions().values()
            ]
            self.assertEqual(sorted(expected), ys)
            # vertical lines: the centerline and the buttocks
            xs = sorted(
                round(pts[0][0], 6)
                for pts in (
                    [tuple(p)[:2] for p in e.points()]
                    for e in doc.modelspace()
                    if e.dxf.layer == "grid" and e.dxftype() == "POLYLINE"
                )
                if pts[0][0] == pts[1][0]
            )
            self.assertEqual([0.0, 500.0, 1000.0, 1500.0], xs)

    def test_output_in_mm(self):
        """the default output unit is the unit of the table: millimetres"""
        import ezdxf.units

        self.assertEqual("mm", self.project.output_unit())
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "body.dxf")
            self.project.save_body_lines_as(out, "raw", "half")
            doc = ezdxf.readfile(out)
            self.assertEqual(ezdxf.units.MM, doc.units)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            pts = [tuple(p)[:2] for e in red for p in e.points()]
            # the table values, in millimetres: the sheer at station 9 is
            # 1535 mm out and 2644 mm high
            self.assertTrue(
                any(abs(x - 1535) < 1e-6 and abs(y - 2644) < 1e-6 for x, y in pts)
            )
            # another unit on request
            self.project.set_output_unit("m")
            self.project.save_body_lines_as(out, "raw", "half")
            pts = [
                tuple(p)[:2]
                for e in ezdxf.readfile(out).modelspace()
                if e.dxf.layer == "red"
                for p in e.points()
            ]
            self.assertTrue(
                any(abs(x - 1.535) < 1e-9 and abs(y - 2.644) < 1e-9 for x, y in pts)
            )

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
            # midship station, and the sheer and keel lines of each side (no
            # rabbet)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            self.assertEqual(14 + 2 + 2, len(red))


if __name__ == "__main__":
    unittest.main()
