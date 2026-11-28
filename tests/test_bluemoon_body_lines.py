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
        # F is the forward end, the table has its sheer only
        self.assertEqual(
            ["F", "1", "2", "3", "4", "5", "6", "7", "8", "TRAN."], list(lines.keys())
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
            [1] * 9 + [2], sorted(len(polys) for polys in default.values())
        )

    def test_station_5_sheer_point(self):
        (poly,) = self.project.body_lines("raw")["5"]
        # SHEER breadth 4-4-0 == 52.0; LWL to SHEER 2-0-3 + LWL above base
        top = poly[0]
        self.assertEqual(52.0, top[0])
        self.assertEqual(
            table_of_offsets.TableOfOffsets.offset2double("2-0-3")
            + self.project._y_lwl,
            top[1],
        )

    def test_diagonal_plan_lines_are_the_table_cells(self):
        # in the plan view the diagonal is drawn as the table says: D. LOWER at
        # the station 6 is 1-8-6 (the patch of the misprint 2-2-4) from the
        # centerline
        origin_y = self.project.plan_centerline_y()
        lines = self.project.loft_diagonal_plan_lines()
        x6 = self.project.station_positions()["6"]
        d1 = dict(lines["D1"])
        self.assertAlmostEqual(
            table_of_offsets.TableOfOffsets.offset2double("1-8-6"),
            origin_y - d1[x6],
        )

    def test_patch_of_the_misprint(self):
        # D. LOWER at the station 6 is 2-2-4 in the book, a misprint; the CSV
        # keeps it, the meta file patches it (1-8-6)
        (patch,) = self.project.patches()
        self.assertEqual(("D. LOWER", "6", "2-2-4", "1-8-6"), patch[:4])
        offset = table_of_offsets.TableOfOffsets.offset2double
        checks = self.project.check_diagonals(self.project.body_points())
        self.assertEqual(14, len(checks))
        self.assertEqual([], [c for c in checks if c.suspect])
        (c6,) = [c for c in checks if (c.row, c.station) == ("D. LOWER", "6")]
        self.assertEqual(offset("1-8-6"), c6.table)
        self.assertIn(
            "patched, the CSV has 2-2-4", self.project.diagonal_check_report(checks)
        )

    def test_check_diagonals_finds_the_misprint(self):
        # the cell of the book: the hull made of the other rows crosses the
        # diagonal at about 21.6 (20.8 with dwl = 49.0)
        offset = table_of_offsets.TableOfOffsets.offset2double
        row = self.project.line_to_index("D. LOWER")
        self.project._too.loc[row, "6"] = "2-2-4"
        checks = self.project.check_diagonals(self.project.body_points())
        (suspect,) = [c for c in checks if c.suspect]
        self.assertEqual(("D. LOWER", "6"), (suspect.row, suspect.station))
        self.assertEqual(offset("2-2-4"), suspect.table)
        self.assertAlmostEqual(21.6, suspect.hull, delta=0.5)
        self.assertIn("SUSPECT", self.project.diagonal_check_report(checks))

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
            self.assertEqual(10 + 2 + 2 + 2, len(red))
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
            # the waterlines are named where the profile view ends
            end = max(self.project.station_positions().values()) + self.project.inches(
                13
            )
            texts = {
                t.dxf.text
                for t in doc.modelspace().query("TEXT")
                if abs(t.dxf.insert.x - end) < 1e-6
            }
            self.assertTrue(set(self.project.waterlines_positions()) <= texts)

    def test_waterline_plan_labels(self):
        """Every waterline line of the plan view is labelled just beyond its
        end with the greatest x"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "blue_moon.dxf")
            self.project.save_model_as(out)
            doc = ezdxf.readfile(out)
        plan_y = self.project.plan_centerline_y()
        texts = [
            (t.dxf.text, t.dxf.insert.x, t.dxf.insert.y)
            for t in doc.modelspace().query("TEXT")
            if t.dxf.insert.y < plan_y + 20
        ]
        for name in self.project.waterlines_positions():
            poly = self.project.loft_line_n_sorted(self.project.line_to_index(name))
            x, y = poly[-1]
            self.assertIn(
                (name, x + self.project.inches(1), y),
                [(n, round(tx, 6), round(ty, 6)) for n, tx, ty in texts],
                name,
            )


if __name__ == "__main__":
    unittest.main()
