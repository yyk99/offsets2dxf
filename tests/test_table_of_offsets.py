"""Tests for table_of_offsets: offset parsing and breadth/height lookup."""

from context import table_of_offsets

import unittest
import os

source_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Test_TableOfOffsets(unittest.TestCase):

    def test_1(self):
        print(table_of_offsets.__version__)
        actual = table_of_offsets.TableOfOffsets()
        self.assertIsNotNone(actual)
        self.assertTrue(actual.verify_triplet("1-2-3"))

    def test_offset2double(self):
        self.assertEqual(1.0, table_of_offsets.TableOfOffsets.offset2double("0-1-0"))
        self.assertEqual(1.0, table_of_offsets.TableOfOffsets.offset2double("0-1"))
        self.assertEqual(12.0, table_of_offsets.TableOfOffsets.offset2double("1-0"))

        self.assertEqual(
            0.1875, table_of_offsets.TableOfOffsets.offset2double("0-0-1+")
        )
        self.assertEqual(
            0.0625, table_of_offsets.TableOfOffsets.offset2double("0-0-1-")
        )

        with self.assertRaises(Exception):
            table_of_offsets.TableOfOffsets.offset2double("0-0-1--")
        with self.assertRaises(Exception):
            table_of_offsets.TableOfOffsets.offset2double("")
        with self.assertRaises(Exception):
            table_of_offsets.TableOfOffsets.offset2double("a-b-c")

    def test_Model(self):
        actual = table_of_offsets.Model(
            os.path.join(source_directory, "sample_data/offset_table.csv")
        )
        self.assertIsNotNone(actual._too)

        stations = actual.station_positions()
        self.assertIs(type(stations), dict)
        self.assertEqual(18, len(stations))

        actual_sheer = actual.loft_sheer()
        # print(sheer)
        """
        [
            (12, 22.25), (36, 20.75), (60, 19.875), (84, 19.25), 
            (108, 19.0), (132, 18.875), (156, 19.125), (180, 19.75), 
            (204, 20.625), (228, 21.625), (252, 23.0), (276, 24.75), 
            (300, 26.625), (324, 28.875), (348, 31.25), (372, 34.0), (396, 36.875)
        ]"""
        expected_sheer = [
            (12, 22.25),
            (36, 20.75),
            (60, 19.875),
            (84, 19.25),
            (108, 19.0),
            (132, 18.875),
            (156, 19.125),
            (180, 19.75),
            (204, 20.625),
            (228, 21.625),
            (252, 23.0),
            (276, 24.75),
            (300, 26.625),
            (324, 28.875),
            (348, 31.25),
            (372, 34.0),
            (396, 36.875),
        ]

        self.assertEqual(17, len(actual_sheer))
        self.assertEqual(expected_sheer, actual_sheer)

        actual_b3 = actual.loft_b3()
        self.assertEqual(13, len(actual_b3))

        actual_bottom, actual_top = actual.drawing_area_vertical_borders()
        self.assertEqual(-120, actual_bottom)
        self.assertEqual(120, actual_top)

    def test_DXF(self):
        # clean up the workspace
        if os.path.exists("test_DXF.dxf"):
            os.remove("test_DXF.dxf")
        self.assertFalse(os.path.exists("test_DXF.dxf"))

        # Test:
        # - create dxf object
        # - close
        # ASSERT: output file is created
        actual_dxf = table_of_offsets.DXF("test_DXF.dxf")
        actual_dxf.close()
        self.assertTrue(os.path.exists("test_DXF.dxf"))

        # - remove output
        os.remove("test_DXF.dxf")
        self.assertFalse(os.path.exists("test_DXF.dxf"))

        # close the object
        # ASSERT: output is not created
        actual_dxf.close()
        self.assertFalse(os.path.exists("test_DXF.dxf"))

    def test_DXF_2(self):
        """Test __exit__ method"""
        # clean up the workspace
        if os.path.exists("test_DXF_2.dxf"):
            os.remove("test_DXF_2.dxf")
        self.assertFalse(os.path.exists("test_DXF_2.dxf"))

        # Test:
        # - create dxf object
        # - call __exit__
        # ASSERT: output file is created
        with table_of_offsets.DXF("test_DXF_2.dxf") as actual_dxf:
            self.assertIs(type(actual_dxf), table_of_offsets.DXF)
            actual_dxf.add_grid_polyline([(0, 0), (10, 10)])

        self.assertTrue(os.path.exists("test_DXF_2.dxf"))


if __name__ == "__main__":
    unittest.main()


class Test_Units(unittest.TestCase):
    def test_offset_to_inches(self):
        f = table_of_offsets.offset_to_inches
        self.assertEqual(22.25, f("1-10-2"))  # the default is feet-inches-eighths
        self.assertEqual(22.25, f("1-10-2", "ftin"))
        self.assertEqual(2.5, f("2.5", "inch"))
        self.assertEqual(24.0, f("2", "ft"))
        self.assertAlmostEqual(50.0, f("1270", "mm"))
        self.assertAlmostEqual(50.0, f("127", "cm"))
        self.assertAlmostEqual(39.37007874, f("1", "m"))
        with self.assertRaises(ValueError):
            f("1", "furlong")
        with self.assertRaises(ValueError):
            f("abc", "mm")

    def test_model_unit(self):
        csv = os.path.join(source_directory, "sample_data", "offset_table.csv")
        model = table_of_offsets.Model(csv)
        self.assertEqual("ftin", model.offsets_unit())
        self.assertEqual("inch", model.units())
        with self.assertRaises(ValueError):
            table_of_offsets.Model(csv, unit="furlong")


class Test_OutputUnit(unittest.TestCase):
    def draw(self, unit):
        import tempfile

        import ezdxf

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "unit.dxf")
            kwargs = {} if unit is None else {"unit": unit}
            with table_of_offsets.DXF(out, **kwargs) as dxf:
                dxf.add_red_polyline([(0, 0), (10, 20)])
                dxf.text((10, 20), "A")
            doc = ezdxf.readfile(out)
        msp = doc.modelspace()
        poly = [e for e in msp if e.dxftype() == "POLYLINE"][0]
        text = [e for e in msp if e.dxftype() == "TEXT"][0]
        return doc, [tuple(p)[:2] for p in poly.points()], text

    def test_dxf_unit(self):
        import ezdxf.units

        # the default: inches, as given
        doc, pts, text = self.draw(None)
        self.assertEqual(ezdxf.units.IN, doc.units)
        self.assertEqual([(0, 0), (10, 20)], pts)
        self.assertEqual(1.0, text.dxf.height)

        # the coordinates (and the text height) are converted from inches
        doc, pts, text = self.draw("mm")
        self.assertEqual(ezdxf.units.MM, doc.units)
        self.assertAlmostEqual(254.0, pts[1][0])
        self.assertAlmostEqual(508.0, pts[1][1])
        self.assertAlmostEqual(25.4, text.dxf.height)
        self.assertAlmostEqual(254.0, text.dxf.align_point.x)

        doc, pts, _ = self.draw("ft")
        self.assertEqual(ezdxf.units.FT, doc.units)
        self.assertAlmostEqual(10 / 12.0, pts[1][0])

        with self.assertRaises(ValueError):
            table_of_offsets.DXF("x.dxf", unit="ftin")

    def test_model_output_unit(self):
        csv = os.path.join(source_directory, "sample_data", "offset_table.csv")
        model = table_of_offsets.Model(csv)  # ftin
        self.assertEqual("inch", model.output_unit())  # the same as the input
        model.set_output_unit("mm")
        self.assertEqual("mm", model.output_unit())
        model.set_output_unit(None)
        self.assertEqual("inch", model.output_unit())
        with self.assertRaises(ValueError):
            model.set_output_unit("ftin")

        mm = table_of_offsets.Model(
            os.path.join(
                source_directory,
                "sample_data",
                "a_ferrocement_hull",
                "offset_table.csv",
            ),
            unit="mm",
        )
        self.assertEqual("mm", mm.output_unit())

    def test_script_args(self):
        f = table_of_offsets.parse_script_args
        self.assertIsNone(f([]).output_units)
        self.assertEqual("mm", f(["--output-units", "mm"]).output_units)
        with self.assertRaises(SystemExit):
            f(["--output-units", "furlong"])


class Test_WaterlineBodyPoints(unittest.TestCase):
    """the waterlines that are in the table are always body line points"""

    class Model(table_of_offsets.Model):
        def waterlines_positions(self):
            # "LWL" and 'WL + 6"' are rows of the table, "NOT IN TABLE" is not
            return {"LWL": 0.0, 'WL + 6"': 6.0, "NOT IN TABLE": 99.0}

    def setUp(self):
        csv = os.path.join(source_directory, "sample_data", "offset_table.csv")
        self.model = self.Model(csv)

    def test_waterline_body_points(self):
        self.assertEqual(
            [("LWL", 0.0), ('WL + 6"', 6.0)], self.model.waterline_body_points()
        )

    def test_added_to_every_body_line(self):
        # no body_points given: the body line is made of the waterlines only
        lines = self.model.loft_body_lines([], "raw")
        # LWL at station 18: breadth 3-9-6, height 0
        self.assertIn((45.75, 0.0), lines["18"][0])
        # WL + 6" at station 18: breadth 4-1-1
        self.assertIn((49.125, 6.0), lines["18"][0])
        # and the link from the lowest point to the centerline
        self.assertEqual(3, len(lines["18"][0]))
        self.assertEqual((0.0, 0.0), lines["18"][0][-1])
        no_link = self.model.loft_body_lines([], "raw", keel_link=False)
        self.assertEqual(2, len(no_link["18"][0]))
        # no point at the stations where the cells are empty
        self.assertEqual([], lines["33"])

    def test_waterline_row(self):
        class Renamed(self.Model):
            def waterline_row(self, name):
                return {"LWL": "Sheer"}.get(name, name)

        csv = os.path.join(source_directory, "sample_data", "offset_table.csv")
        # the breadth of "LWL" is taken from the row "Sheer"
        self.assertEqual(
            [("Sheer", 0.0), ('WL + 6"', 6.0)], Renamed(csv).waterline_body_points()
        )


class Test_Diagonals(unittest.TestCase):
    """the diagonals: (y0, x1, y1), the table gives the distance along the
    line from (0, y0)"""

    class Model(table_of_offsets.Model):
        def diagonals_positions(self):
            # a 3-4-5 line: from (0, 10) through (24, 28); "NOT IN TABLE" has
            # no row
            return {"1": (10.0, 24.0, 28.0), "NOT IN TABLE": (0.0, 1.0, 1.0)}

        def diagonal_row(self, name):
            return "Diagonal " + name

    def setUp(self):
        csv = os.path.join(source_directory, "sample_data", "offset_table.csv")
        self.model = self.Model(csv)

    def test_default_has_no_diagonals(self):
        model = table_of_offsets.Model(
            os.path.join(source_directory, "sample_data", "offset_table.csv")
        )
        self.assertEqual({}, model.diagonals_positions())
        self.assertEqual([], model.diagonal_body_points())
        self.assertEqual("Diagonal 1", model.diagonal_row("Diagonal 1"))

    def test_diagonal_point(self):
        point = table_of_offsets.DiagonalPoint("row", 10.0, 24.0, 28.0)
        # the direction (24, 18) / 30 = (0.8, 0.6)
        x, y = point.point(10.0)
        self.assertAlmostEqual(8.0, x)
        self.assertAlmostEqual(16.0, y)
        self.assertEqual((0.0, 10.0), point.point(0.0))
        with self.assertRaises(ValueError):
            table_of_offsets.DiagonalPoint("row", 5.0, 0.0, 5.0)

    def test_body_points_of_the_diagonals(self):
        (point,) = self.model.diagonal_body_points()  # the row is in the table
        self.assertEqual("Diagonal 1", point.row)

    def test_body_line_points(self):
        lines = self.model.loft_body_lines([], "raw")
        # station 18: Diagonal 1 is 1-6-2 = 18.25 in
        x, y = 0.8 * 18.25, 10.0 + 0.6 * 18.25
        self.assertEqual(1, len(lines["18"][0]) - 1)  # and the keel link
        self.assertAlmostEqual(x, lines["18"][0][0][0])
        self.assertAlmostEqual(y, lines["18"][0][0][1])
        # the stations without the cell have no point
        self.assertEqual([], lines["33"])

    def test_plan_lines(self):
        """the diagonal in the plan view is below the centerline: y = origin
        - half-breadth of the hull point"""
        lines = self.model.loft_diagonal_plan_lines(origin_y=100.0)
        self.assertEqual(["1"], list(lines))
        positions = self.model.station_positions()
        poly = lines["1"]
        # one point per station that has the cell, in the order of the stations
        cells = [
            s
            for s in positions
            if isinstance(
                self.model._too.loc[self.model.line_to_index("Diagonal 1"), s], str
            )
        ]
        self.assertEqual([positions[s] for s in cells], [x for x, _ in poly])
        # station 18: 18.25 in along the diagonal (0.8, 0.6): half-breadth 14.6
        self.assertIn((positions["18"], 100.0 - 0.8 * 18.25), poly)
        for _, y in poly:
            self.assertLess(y, 100.0)
        # the default origin: 0, as there is one grid_y_origins only
        default = self.model.loft_diagonal_plan_lines()
        self.assertEqual(len(poly), len(default["1"]))
        for (x, y), (x2, y2) in zip(poly, default["1"]):
            self.assertEqual(x, x2)
            self.assertAlmostEqual(y - 100.0, y2)

    def test_segments(self):
        segments = self.model.diagonal_segments(5.0, both=True)
        self.assertEqual(
            {"1": [((5.0, 10.0), (29.0, 28.0)), ((5.0, 10.0), (-19.0, 28.0))]},
            {k: v for k, v in segments.items() if k == "1"},
        )

    def test_segments_extension(self):
        """the diagonal runs ``diagonal_extension()`` beyond the farthest hull
        point (0.8, 0.6 per inch along it)"""
        far = max(
            self.model.offset_to_inches(c)
            for c in self.model._too.loc[
                self.model.line_to_index("Diagonal 1"),
                list(self.model.station_positions()),
            ]
            if isinstance(c, str)
        )
        self.model.diagonal_extension = lambda: 3.0
        segments = self.model.diagonal_segments(5.0, both=True)
        (a, b), (c, d) = segments["1"]
        self.assertEqual((5.0, 10.0), a)
        self.assertAlmostEqual(5.0 + 0.8 * (far + 3.0), b[0])
        self.assertAlmostEqual(10.0 + 0.6 * (far + 3.0), b[1])
        self.assertAlmostEqual(5.0 - 0.8 * (far + 3.0), d[0])


class Test_Output(unittest.TestCase):
    def test_output_dir_from_args(self):
        f = table_of_offsets.output_dir_from_args
        # ./out in the current directory by default, whatever it is
        self.assertEqual(os.path.join(os.getcwd(), "out"), f([]))
        self.assertEqual("out", table_of_offsets.DEFAULT_OUT_DIR)
        cwd = os.getcwd()
        try:
            os.chdir(os.path.join(source_directory, "tests"))
            self.assertEqual(os.path.join(source_directory, "tests", "out"), f([]))
        finally:
            os.chdir(cwd)
        self.assertEqual(os.path.abspath("elsewhere"), f(["--out-dir", "elsewhere"]))

    def test_dxf_creates_the_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "new", "sub", "file.dxf")
            with table_of_offsets.DXF(out) as dxf:
                dxf.add_polyline([(0, 0), (1, 1)])
            self.assertTrue(os.path.exists(out))


class Test_BodyLine(unittest.TestCase):
    """breadth_at / height_at / loft_body_line on sample_data/offset_table.csv"""

    def setUp(self):
        self.model = table_of_offsets.Model(
            os.path.join(source_directory, "sample_data", "offset_table.csv")
        )

    def test_breadth_at(self):
        # Sheer at station 32 is 1-10-2
        self.assertEqual(22.25, self.model.breadth_at("32", "Sheer"))

    def test_height_at(self):
        # B 1' at station 30 is 0-3-4
        self.assertEqual(3.5, self.model.height_at("30", "B 1'"))

    def test_loft_body_line(self):
        poly = self.model.loft_body_line("30", [("Sheer", "B 1'"), "Rabbet"])
        self.assertEqual([(20.75, 3.5), (0.25, 0.25)], poly)

    def test_errors(self):
        with self.assertRaises(KeyError):
            self.model.breadth_at("32", "nope")
        with self.assertRaises(KeyError):
            self.model.breadth_at("99", "Sheer")
        with self.assertRaises(ValueError):
            self.model.breadth_at("33", "Sheer")  # empty cell
