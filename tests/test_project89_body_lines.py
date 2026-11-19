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
        lines = self.project.body_lines("max_breadth", "half")
        self.assertEqual(18, len(lines))
        for station, polys in lines.items():
            (poly,) = polys
            heights = [y for _, y in poly]
            self.assertEqual(sorted(heights, reverse=True), heights, station)
        # 13 points and the horizontal link from the keel to the centerline
        self.assertEqual(14, len(lines["18"][0]))
        self.assertEqual(self.project.body_plan_centerline_x, lines["18"][0][-1][0])

    def test_default_sides(self):
        model = table_of_offsets.Model
        # in the middle of the profile view: split; otherwise: half
        self.assertEqual("split", model.body_plan_sides("max_breadth"))
        self.assertEqual("half", model.body_plan_sides("right"))
        self.assertEqual("half", model.body_plan_sides("raw"))
        self.assertEqual("both", model.body_plan_sides("max_breadth", "both"))

        default = self.project.body_lines()
        self.assertEqual(default, self.project.body_lines("max_breadth", "split"))
        # the midship station is drawn on both sides, the others on one
        counts = sorted(len(p) for p in default.values())
        self.assertEqual([1] * 17 + [2], counts)
        self.assertEqual(
            self.project.body_lines("right", "half"), self.project.body_lines("right")
        )
        self.assertEqual(
            self.project.body_lines("raw", "half"), self.project.body_lines("raw")
        )

    def test_station_18_points(self):
        (poly,) = self.project.body_lines("raw")["18"]
        # the sheer is the top point: 1/2w Deck 4-3-0 at height Sheer 1-7-6
        self.assertEqual((51.0, 19.75), poly[0])
        # the LWL point: breadth 3-9-6, height 0
        self.assertIn((45.75, 0.0), poly)

    def test_placement(self):
        raw = self.project.body_lines("raw")
        widest = max(raw, key=lambda s: max(x for x, _ in raw[s][0]))
        positions = self.project.station_positions()

        mid = self.project.body_lines("max_breadth", "half")
        self.assertEqual(raw[widest][0][0][0] + positions[widest], mid[widest][0][0][0])
        self.assertEqual(raw["18"][0][0][1], mid["18"][0][0][1])  # y is not changed

        right = self.project.body_lines("right")
        left_edge = min(
            x for p in table_of_offsets.Model.body_polylines(right) for x, _ in p
        )
        self.assertGreater(left_edge, max(positions.values()))

        with self.assertRaises(ValueError):
            self.project.body_lines("nowhere")

    def test_sides(self):
        positions = self.project.station_positions()
        raw = self.project.body_lines("raw")
        widest = max(raw, key=lambda s: max(x for x, _ in raw[s][0]))

        both = self.project.body_lines("raw", "both")
        (poly,) = both["18"]
        (half,) = raw["18"]
        # the keel point on the centerline is shared by the two halves
        self.assertEqual(2 * len(half) - 1, len(poly))
        self.assertEqual(half[0], poly[0])
        self.assertEqual((-half[0][0], half[0][1]), poly[-1])

        split = self.project.body_lines("raw", "split")
        for station, polys in split.items():
            xs = positions[station]
            sides = [p[0][0] > 0 for p in polys if p]
            if station == widest:
                self.assertEqual([False, True], sides)
            elif xs < positions[widest]:
                self.assertEqual([False], sides, station)  # aft: left
            else:
                self.assertEqual([True], sides, station)  # forward: right

        with self.assertRaises(ValueError):
            self.project.body_lines("raw", "nowhere")

    def test_bow_station(self):
        positions = self.project.station_positions()
        self.assertEqual("0", self.project.bow_station())
        default = self.project.body_lines("raw", "split")

        # the bow at the other end: forward and aft swap
        self.project.set_bow_station("33")
        swapped = self.project.body_lines("raw", "split")
        for station in ("30", "6"):
            # a station aft of the midship is on the left, forward on the right
            self.assertEqual(1, len(default[station]))
            self.assertEqual(1, len(swapped[station]))
            self.assertNotEqual(
                default[station][0][0][0] > 0, swapped[station][0][0][0] > 0, station
            )
        # the argument overrides the setting
        back = self.project.body_lines("raw", "split", bow_station="0")
        self.assertEqual(default, back)

        with self.assertRaises(KeyError):
            self.project.set_bow_station("99")
        raw = self.project.body_lines("raw")
        widest = max(raw, key=lambda s: max(x for x, _ in raw[s][0]))
        with self.assertRaises(ValueError):
            self.project.body_lines("raw", "split", bow_station=widest)

    def test_right_placement_keeps_left_half_clear(self):
        lines = self.project.body_lines("right", "split")
        xs = [x for p in self.project.body_polylines(lines) for x, _ in p]
        self.assertGreater(min(xs), max(self.project.station_positions().values()))

    def test_grid_for_right_placement(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "p89_right.dxf")
            self.project.save_model_as(out, body_placement="right")
            doc = ezdxf.readfile(out)
            grid = [
                [tuple(p)[:2] for p in e.points()]
                for e in doc.modelspace()
                if e.dxf.layer == "grid" and e.dxftype() == "POLYLINE"
            ]
            lines = self.project.body_lines("right")
            body_x = max(x for p in self.project.body_polylines(lines) for x, _ in p)
            cl_x = self.project.body_plan_centerline_x

            # the base line (y == 0) and the waterlines run through the body plan
            for y in (0, 12.0, -12.0):
                reach = max(x for g in grid for x, gy in g if gy == y)
                self.assertGreater(reach, body_x, y)
            # a vertical centerline of the body plan
            vertical = [g for g in grid if len(g) == 2 and g[0][0] == g[1][0] == cl_x]
            self.assertEqual(1, len(vertical))

    def test_buttocks_in_body_plan(self):
        def vertical_grid_x(**kwargs):
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "p89.dxf")
                self.project.save_model_as(out, **kwargs)
                doc = ezdxf.readfile(out)
                xs = set()
                for e in doc.modelspace():
                    if e.dxf.layer == "grid" and e.dxftype() == "POLYLINE":
                        pts = [tuple(p)[:2] for p in e.points()]
                        if len(pts) == 2 and pts[0][0] == pts[1][0]:
                            xs.add(pts[0][0])
                # leave out the station lines
                return xs - set(self.project.station_positions().values())

        project = self.project
        right = vertical_grid_x(body_placement="right")
        cl = project.body_plan_centerline_x
        for offset in project.buttocks_positions().values():
            self.assertIn(cl + offset, right)
            self.assertNotIn(cl - offset, right)

        both = vertical_grid_x(body_placement="right", body_sides="split")
        cl = project.body_plan_centerline_x
        for offset in project.buttocks_positions().values():
            self.assertIn(cl + offset, both)
            self.assertIn(cl - offset, both)

        # nothing is added for the default placement
        default = vertical_grid_x()
        self.assertEqual(set(), default)

    def test_no_centerline_for_default_placement(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "p89.dxf")
            self.project.save_model_as(out)
            doc = ezdxf.readfile(out)
            texts = [e.dxf.text for e in doc.modelspace() if e.dxftype() == "TEXT"]
            self.assertNotIn("CL", texts)

    def test_body_lines_file_has_grid(self):
        """the body lines file shows the grid: base line, CL, waterlines and
        buttocks"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "p89_body.dxf")
            self.project.save_body_lines_as(out)
            msp = ezdxf.readfile(out).modelspace()
            grid = [e for e in msp if e.dxf.layer == "grid"]
            labels = [e.dxf.text for e in msp if e.dxftype() == "TEXT"]
            n_wl = len(self.project.waterlines_positions())
            n_b = len(self.project.buttocks_positions())
            # base line + waterlines + CL + buttocks on both sides (split)
            self.assertEqual(1 + n_wl + 1 + 2 * n_b, len(grid))
            self.assertIn("CL", labels)
            self.assertIn("baseline", labels)
            for name in self.project.waterlines_positions():
                self.assertIn(name, labels)

    def test_sheer_line(self):
        """the sheer points of the consecutive stations are joined, one line
        per side of the centerline"""
        lines = self.project.body_lines("raw", "split")
        left, right = None, None
        for poly in self.project.body_sheer_polylines(lines):
            if poly[0][0] < 0:
                left = poly
            else:
                right = poly
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        # the points are the sheer points of the table, not the highest points
        first = ("1/2w Deck", "Sheer")
        expected = []
        for station, polys in lines.items():
            sp = self.project.loft_body_line(station, [first], skip_missing=True)
            for poly in polys:
                if sp:
                    expected.append(
                        (sp[0][0] if poly[0][0] > 0 else -sp[0][0], sp[0][1])
                    )
        self.assertEqual(sorted(expected), sorted(left + right))
        self.assertEqual(len(left), len(set(left)))
        # half: only one line, on the right
        half = self.project.body_lines("raw", "half")
        (only,) = self.project.body_sheer_polylines(half)
        # a station without the sheer cell is skipped
        n_sheer = len(
            [s for s in half if self.project.loft_body_line(s, [first], True)]
        )
        self.assertEqual(len(only), n_sheer)
        self.assertLess(n_sheer, len([s for s in half if half[s]]))
        # both: the sheer of the left half is the mirror of the right one
        both = self.project.body_lines("raw", "both")
        l, r = sorted(self.project.body_sheer_polylines(both), key=lambda p: p[0][0])
        self.assertEqual(sorted((-x, y) for x, y in l), sorted(r))

    def test_rabbet_line(self):
        """the rabbet points of the consecutive stations are joined, one line
        per side of the centerline"""
        lines = self.project.body_lines("raw", "split")
        rabbet = self.project.body_rabbet_polylines(lines)
        self.assertEqual(2, len(rabbet))
        point = self.project.rabbet_body_point()
        expected = []
        for station, polys in lines.items():
            rp = self.project.loft_body_line(station, [point], skip_missing=True)
            for poly in polys:
                if rp:
                    expected.append(
                        (rp[0][0] if poly[0][0] > 0 else -rp[0][0], rp[0][1])
                    )
        self.assertEqual(sorted(expected), sorted(rabbet[0] + rabbet[1]))

        # a model without the rabbet has no rabbet line
        class NoRabbet(type(self.project)):
            def rabbet_body_point(self):
                return None

        self.assertEqual([], NoRabbet().body_rabbet_polylines(NoRabbet().body_lines()))

    def test_keel_line(self):
        """the keel points of the consecutive stations are joined, one line
        per side of the centerline"""
        lines = self.project.body_lines("raw", "split")
        keel = self.project.body_keel_polylines(lines)
        self.assertEqual(2, len(keel))
        point = self.project.keel_body_point()
        expected = []
        for station, polys in lines.items():
            kp = self.project.loft_body_line(station, [point], skip_missing=True)
            for poly in polys:
                if kp:
                    expected.append(
                        (kp[0][0] if poly[0][0] > 0 else -kp[0][0], kp[0][1])
                    )
        self.assertEqual(sorted(expected), sorted(keel[0] + keel[1]))

    def test_station_labels(self):
        """every body line has its station name above its top end"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "p89_body.dxf")
            self.project.save_body_lines_as(out)
            doc = ezdxf.readfile(out)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            lines = self.project.body_lines()
            # the grid labels (CL, waterlines, buttocks) are texts as well
            texts = [
                e
                for e in doc.modelspace()
                if e.dxftype() == "TEXT" and e.dxf.text in lines
            ]
            # a label per body line; the sheer lines have none
            lines = self.project.body_lines()
            n_extra = (
                len(self.project.body_sheer_polylines(lines))
                + len(self.project.body_rabbet_polylines(lines))
                + len(self.project.body_keel_polylines(lines))
            )
            self.assertEqual(len(red) - n_extra, len(texts))

            expected = sorted(
                (
                    station,
                    round(max(p, key=lambda pt: pt[1])[0], 3),
                    round(max(p, key=lambda pt: pt[1])[1] + 1, 3),
                )
                for station, polys in lines.items()
                for p in polys
            )
            actual = sorted(
                (
                    e.dxf.text,
                    round(e.dxf.align_point.x, 3),
                    round(e.dxf.align_point.y, 3),
                )
                for e in texts
            )
            self.assertEqual(expected, actual)

    def test_generate_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "project89_body.dxf")
            self.project.save_body_lines_as(out)  # the default: split
            doc = ezdxf.readfile(out)
            red = [e for e in doc.modelspace() if e.dxf.layer == "red"]
            # one polyline per station, two for the midship station, and the
            # sheer, rabbet and keel lines of each side
            self.assertEqual(19 + 2 + 2 + 2, len(red))


if __name__ == "__main__":
    unittest.main()
