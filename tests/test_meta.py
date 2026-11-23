from context import table_of_offsets

import os
import tempfile
import unittest

CSV = os.path.join(os.path.dirname(__file__), "../sample_data/offset_table.csv")
META = os.path.join(os.path.dirname(__file__), "../sample_data/offset_table.meta")


class Test_LoadMeta(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x.meta")
            with open(path, "w") as f:
                f.write(text)
            return table_of_offsets.load_meta(path)

    def test_sample(self):
        meta = table_of_offsets.load_meta(META)
        self.assertEqual("ftin", meta["table"]["unit"])
        self.assertEqual(3, len(meta["diagonals"]))

    def test_find_meta(self):
        find = table_of_offsets.find_meta
        with tempfile.TemporaryDirectory() as tmp:
            csv = os.path.join(tmp, "t.csv")
            self.assertIsNone(find(csv))
            open(os.path.join(tmp, "t.grid"), "w").close()
            self.assertEqual(os.path.join(tmp, "t.grid"), find(csv))
            os.remove(os.path.join(tmp, "t.grid"))
            open(os.path.join(tmp, "t.meta"), "w").close()
            self.assertEqual(os.path.join(tmp, "t.meta"), find(csv))
            open(os.path.join(tmp, "t.grid"), "w").close()
            with self.assertRaises(ValueError):  # both
                find(csv)

    def test_errors(self):
        for text in [
            "[nope]\n",
            "[table]\nnope = 1\n",
            '[table]\nunit = "furlong"\n',
            '[table]\nmulti_value = "nope"\n',
            "[stations]\norigin = 33\n",
            '[stations]\nspacing = "x"\n',
            "[stations]\n",
            '[stations]\npositions = { FP = "x" }\n',
            '[buttocks]\nB = "x"\n',
            "[waterlines]\nLWL = { depth = 1 }\n",
            "[waterlines]\nLWL = {}\n",
            "[diagonals]\nD = { from = [1, 0], through = [2, 2] }\n",
            "[diagonals]\nD = { from = [0, 0] }\n",
            "[ghost_line]\nrow = 1\n",
            "[sheet]\nvertical_borders = [1]\n",
            "[table\n",
        ]:
            with self.assertRaises(ValueError, msg=text):
                self.load(text)


class Test_StationNames(unittest.TestCase):
    """stations are strings: "1", "T", "AP", "FP", "1A" ..."""

    CSV = "#,FP,1A,1,2,T\nSheer,1350,1240,1158,1048,1142\n"

    def model(self, meta_text, csv=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        csv_path = os.path.join(tmp.name, "t.csv")
        with open(csv_path, "w") as f:
            f.write(csv or self.CSV)
        with open(os.path.join(tmp.name, "t.meta"), "w") as f:
            f.write(meta_text)
        return table_of_offsets.Model(csv_path, unit="mm")

    def assertMm(self, expected_mm, actual_inches):
        self.assertEqual(expected_mm.keys(), actual_inches.keys())
        for k, v in expected_mm.items():
            self.assertAlmostEqual(v, actual_inches[k], msg=k)

    def test_positions(self):
        model = self.model(
            "[table]\nunit = 'mm'\n"
            "[stations.positions]\nFP = 3000\n'1A' = 2500.5\n"
            "'1' = 2000\n'2' = 1000\nT = 0\n"
        )
        # the lengths of the file are in millimetres, the model has millimetres too
        self.assertMm(
            {"FP": 3000.0, "1A": 2500.5, "1": 2000.0, "2": 1000.0, "T": 0.0},
            model.station_positions(),
        )
        self.assertAlmostEqual(1240, model.breadth_at("1A", "Sheer"))

    def test_positions_and_spacing(self):
        """the stations not in positions: by their place in the list"""
        model = self.model(
            "[table]\nunit = 'mm'\n"
            "[stations]\nspacing = 1000\n"
            "positions = { FP = 3000, T = -100 }\n"
        )
        self.assertMm(
            {"FP": 3000.0, "1A": 1000, "1": 2000, "2": 3000, "T": -100.0},
            model.station_positions(),
        )

    def test_origin_and_negative_spacing(self):
        """x = origin + n * spacing; negative spacing: the first is the bow"""
        model = self.model(
            "[table]\nunit = 'mm'\n[stations]\norigin = 4000\nspacing = -1000\n"
        )
        self.assertMm(
            {"FP": 4000, "1A": 3000, "1": 2000, "2": 1000, "T": 0},
            model.station_positions(),
        )

    def test_default_layout(self):
        """no meta data: the n-th station is at n * 12 inches (a foot) for a
        ftin table, whatever the names; there is no default for the others"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.csv")
            with open(path, "w") as f:
                f.write(self.CSV.replace("1350", "1-1-0"))
            model = table_of_offsets.Model(path, unit="ftin")
            self.assertEqual(
                {"FP": 0, "1A": 12, "1": 24, "2": 36, "T": 48},
                model.station_positions(),
            )
            with open(path, "w") as f:
                f.write(self.CSV)
            model = table_of_offsets.Model(path, unit="mm")
            with self.assertRaises(ValueError):
                model.station_positions()

    def test_errors(self):
        # a name without a position (no spacing)
        model = self.model("[table]\nunit = 'mm'\n[stations.positions]\nFP = 1\n")
        with self.assertRaises(ValueError):
            model.station_positions()
        # a position of a station that is not in the table
        model = self.model(
            "[table]\nunit = 'mm'\n[stations.positions]\nFP = 1\nXX = 2\n"
        )
        with self.assertRaises(ValueError):
            model.station_positions()


class Test_ModelMeta(unittest.TestCase):
    def test_project89_grid(self):
        """the grid of Model(offset_table.csv) comes from the meta data file
        and is the one of project 89 before it had the file"""
        model = table_of_offsets.Model(CSV)
        self.assertEqual("0", model.bow_station())
        self.assertEqual((33 - 14) * 12, model.station_positions()["14"])
        self.assertEqual(396, model.station_positions()["0"])
        self.assertEqual(
            [
                ("WL + 2'", 24.0),
                ("WL + 1'", 12.0),
                ('WL + 6"', 6.0),
                ("LWL", 0.0),
                ('WL - 6"', -6.0),
                ("WL - 1'", -12.0),
                ("WL - 2'", -24.0),
                ("WL - 3'", -36.0),
                ("WL - 4'", -48.0),
            ],
            list(model.waterlines_positions().items()),
        )
        self.assertEqual(
            {"B 3'": 36.0, "B 2'": 24.0, "B 1'": 12.0}, model.buttocks_positions()
        )
        self.assertEqual(
            {
                "D1": (-12.0, 36.0, -36.0),
                "D2": (0.0, 36.0, -36.0),
                "D3": (24.0, 60.0, -6.0),
            },
            model.diagonals_positions(),
        )
        self.assertEqual("Diagonal 1", model.diagonal_row("D1"))
        self.assertEqual("D 3", model.diagonal_row("D3"))
        self.assertEqual("LWL", model.waterline_row("LWL"))
        self.assertEqual(("Profile Plan", -51.0), model.ghost_line())
        self.assertEqual([0.0, 120.0], model.grid_y_origins())
        self.assertEqual((-120.0, 240.0), model.drawing_area_vertical_borders())
        # "0-2-0 and 0-3-0": the first value
        self.assertEqual(2.0, model.breadth_at("20", "Profile Plan"))

    def test_no_meta(self):
        """meta=False: no file; the defaults of the base class"""
        model = table_of_offsets.Model(CSV, unit="ftin", meta=False)
        self.assertIsNone(model.bow_station())
        self.assertIsNone(model.ghost_line())
        self.assertEqual({}, model.diagonals_positions())
        self.assertEqual([0.0], model.grid_y_origins())
        with self.assertRaises(ValueError):
            model.breadth_at("20", "Profile Plan")

    def test_unit(self):
        table_of_offsets.Model(CSV, unit="ftin")
        with self.assertRaises(ValueError):
            table_of_offsets.Model(CSV, unit="mm")  # the file says ftin

    def test_grid_extension(self):
        """a file with the extension .grid is found like .meta"""
        with tempfile.TemporaryDirectory() as tmp:
            csv = os.path.join(tmp, "t.csv")
            with open(csv, "w") as f:
                f.write("#,A,B\nSheer,1,2\n")
            with open(os.path.join(tmp, "t.grid"), "w") as f:
                f.write("[table]\nunit = 'mm'\n[stations]\nspacing = 5\n")
            model = table_of_offsets.Model(csv)
            self.assertAlmostEqual(5, model.station_positions()["B"])
            self.assertEqual("mm", model.offsets_unit())
            # the unit is never guessed
            with self.assertRaises(ValueError):
                table_of_offsets.Model(csv, meta=False)
            other = table_of_offsets.Model(csv, unit="ftin", meta=False)
            self.assertEqual("ftin", other.offsets_unit())

    def test_explicit_path_and_missing_file(self):
        table_of_offsets.Model(CSV, meta=META)
        with self.assertRaises(FileNotFoundError):
            table_of_offsets.Model(CSV, meta="nope.meta")


if __name__ == "__main__":
    unittest.main()


class Test_MetaLengthsInTableUnit(unittest.TestCase):
    def test_lengths_are_in_the_unit_of_the_table(self):
        with tempfile.TemporaryDirectory() as d:
            csv = os.path.join(d, "t.csv")
            with open(csv, "w") as f:
                f.write("#,1,2\nHeight Sheer,100,200\n")
            with open(os.path.join(d, "t.grid"), "w") as f:
                f.write(
                    '[table]\nunit = "mm"\n[stations]\nspacing = 254.0\n'
                    "[buttocks]\nB1 = 508.0\n"
                    "[waterlines]\nWL = { height = 25.4 }\n"
                )
            m = table_of_offsets.Model(csv)
            # not converted
            self.assertAlmostEqual(m.station_positions()["2"], 254.0)
            self.assertAlmostEqual(m.buttocks_positions()["B1"], 508.0)
            self.assertAlmostEqual(m.waterlines_positions()["WL"], 25.4)


class Test_Siding(unittest.TestCase):
    def model(self, text):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write("#,1\nHeight Sheer,100\n")
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(text if "unit" in text else "[table]\nunit = 'ftin'\n" + text)
        return table_of_offsets.Model(csv)

    def test_siding_in_table_unit(self):
        m = self.model(
            '[table]\nunit = "mm"\n[keel]\nsiding = 50.8\n[rabbet]\nsiding = 25.4\n'
        )
        self.assertAlmostEqual(50.8, m.siding("keel"))
        self.assertAlmostEqual(25.4, m.siding("rabbet"))
        self.assertIsNone(m.siding("stem"))
        self.assertEqual(7.0, m.siding("stem", 7.0))

    def test_no_siding(self):
        self.assertIsNone(self.model("[table]\nunit = 'ftin'\n").siding("keel"))

    def test_bad_siding(self):
        for bad in ("siding = 'x'", "siding = 0", "siding = -1"):
            for section in ("keel", "rabbet"):
                with self.assertRaises(ValueError, msg=bad):
                    self.model("[%s]\n%s\n" % (section, bad))


class Test_Keel(unittest.TestCase):
    def model(self, text):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write("#,A,B,C\nHeight Sheer,1,2,3\n")
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(text if "unit" in text else "[table]\nunit = 'ftin'\n" + text)
        return table_of_offsets.Model(csv)

    def test_keel_line(self):
        m = self.model(
            '[table]\nunit = "mm"\n[stations]\nspacing = 254.0\n'
            '[keel]\nfrom = { station = "B", height = 25.4 }\n'
            'to = { station = "C", height = 0 }\n'
        )
        (x0, y0), (x1, y1) = m.keel_line()
        self.assertAlmostEqual(254.0, x0)
        self.assertAlmostEqual(25.4, y0)
        self.assertAlmostEqual(508.0, x1)
        self.assertEqual(0, y1)

    def test_no_keel(self):
        self.assertIsNone(self.model("[table]\nunit = 'mm'\n").keel_line())

    def test_bad_keel(self):
        for text in (
            '[keel]\nfrom = { station = "A" }\nto = { station = "B", height = 0 }\n',
        ):
            with self.assertRaises(ValueError):
                self.model(text)
        m = self.model(
            '[keel]\nfrom = { station = "X", height = 0 }\n'
            'to = { station = "A", height = 0 }\n'
        )
        with self.assertRaises(ValueError):
            m.keel_line()


class Test_KeelPoint(unittest.TestCase):
    def test_keel_point_in_body_lines(self):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write("#,A,B,C\nHeight Sheer,100,100,100\n" "Breadth Sheer,300,300,300\n")
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\n[stations]\nspacing = 100.0\n'
                '[keel]\nfrom = { station = "B", height = 0 }\n'
                'to = { station = "C", height = 10.0 }\nsiding = 40.0\n'
            )
        m = table_of_offsets.Model(csv)
        mm = 1.0  # the model works in mm
        self.assertIsNone(m.keel_point_at("A"))
        x, y = m.keel_point_at("C")
        self.assertAlmostEqual(20 * mm, x)
        self.assertAlmostEqual(10 * mm, y)
        lines = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        # A: no keel point, the link is at the sheer height
        self.assertEqual(
            [(round(p[0] / mm), round(p[1] / mm)) for p in lines["A"][0]],
            [(300, 100), (0, 100)],
        )
        # B: the keel point at height 0 and its link to the centerline
        self.assertEqual(
            [(round(p[0] / mm), round(p[1] / mm)) for p in lines["B"][0]],
            [(300, 100), (20, 0), (0, 0)],
        )


class Test_KeelAndRabbetLines(unittest.TestCase):
    MM = 1.0  # the model works in mm

    def model(self, grid):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C\nHeight Sheer,100,100,100\nBreadth Sheer,300,300,300\n"
                "Height RL,,20,30\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(grid)
        return table_of_offsets.Model(csv)

    GRID = (
        '[table]\nunit = "mm"\n[stations]\nspacing = 100.0\n'
        "[sheet]\ny_origins = [0, -500]\n"
        '[keel]\nfrom = { station = "B", height = 0 }\n'
        'to = { station = "C", height = 0 }\nsiding = 40.0\n'
        '[rabbet]\nheight_row = "Height RL"\nsiding = 60.0\n'
    )

    def mm(self, line):
        return [(round(x / self.MM), round(y / self.MM)) for x, y in line]

    def test_lines(self):
        m = self.model(self.GRID)
        self.assertEqual([(100, 0), (200, 0)], self.mm(m.keel_profile_line()))
        self.assertEqual([(100, 20), (200, 30)], self.mm(m.rabbet_profile_line()))
        # constant half-breadth off the plan centerline (y = -500)
        self.assertEqual([(100, -480), (200, -480)], self.mm(m.keel_plan_line()))
        self.assertEqual([(100, -470), (200, -470)], self.mm(m.rabbet_plan_line()))

    def test_rabbet_body_point(self):
        m = self.model(self.GRID)
        x, row = m.rabbet_body_point()
        self.assertAlmostEqual(30 * self.MM, x)
        self.assertEqual("Height RL", row)
        # loft_body_lines adds it: the rabbet point is in the body lines
        lines = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        self.assertIn(
            (30, 30),
            [(round(x / self.MM), round(y / self.MM)) for x, y in lines["C"][0]],
        )

    def test_nothing_in_the_file(self):
        m = self.model("[table]\nunit = 'mm'\n[stations]\nspacing = 10\n")
        self.assertIsNone(m.keel_profile_line())
        self.assertIsNone(m.rabbet_profile_line())
        self.assertIsNone(m.keel_plan_line())
        self.assertIsNone(m.rabbet_body_point())

    def test_no_plan_view(self):
        m = self.model(self.GRID.replace("y_origins = [0, -500]", "y_origins = [0]"))
        self.assertIsNone(m.plan_centerline_y())
        self.assertIsNone(m.keel_plan_line())

    def test_bad_rabbet_rows(self):
        for text in (
            "[rabbet]\nheight_row = 3\n",
            '[rabbet]\nheight_row = ""\n',
            '[rabbet]\nheight_row = "Height RL"\nbreadth_row = 3\n',
            '[rabbet]\nbreadth_row = "Breadth RL"\n',
            '[rabbet]\nrow = "Height RL"\n',
        ):
            with self.assertRaises(ValueError, msg=text):
                self.model(text)

    def test_rabbet_breadth_row(self):
        """a breadth row of the table wins over the siding"""
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C\nHeight Sheer,100,100,100\nBreadth Sheer,300,300,300\n"
                "Height RL,,20,30\nBreadth RL,,5,8\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\n[stations]\nspacing = 100.0\n'
                "[sheet]\ny_origins = [0, -500]\n"
                '[rabbet]\nheight_row = "Height RL"\nbreadth_row = "Breadth RL"\n'
                "siding = 60.0\n"
            )
        m = table_of_offsets.Model(csv)
        self.assertEqual(("Breadth RL", "Height RL"), m.rabbet_body_point())
        # no base_offset here: the plan line is the breadth row itself
        self.assertEqual([(100, 5), (200, 8)], self.mm(m.rabbet_plan_line()))
        self.assertEqual([(100, 20), (200, 30)], self.mm(m.rabbet_profile_line()))

    def test_plot(self):
        class Dxf:
            def __init__(self):
                self.lines = []

            def add_red_polyline(self, line):
                self.lines.append(line)

        m = self.model(self.GRID)
        dxf = Dxf()
        m.plot_keel_and_rabbet(dxf)
        self.assertEqual(4, len(dxf.lines))
        dxf = Dxf()
        m.plot_keel_and_rabbet(dxf, plan=False)
        self.assertEqual(2, len(dxf.lines))

    def test_rabbet_extra_points(self):
        """extra points, dx right of a station, height above the datum; the
        line stays ordered by x in the direction of the line of the table"""
        grid = self.GRID.replace(
            "siding = 60.0\n",
            "siding = 60.0\nextra_points = [\n"
            '  { station = "A", dx = -30.0, height = 5.0 },\n'
            '  { station = "C", dx = 40.0, height = 9.0 },\n]\n',
        )
        m = self.model(grid)
        self.assertEqual(
            [(-30, 5), (100, 20), (200, 30), (240, 9)], self.mm(m.rabbet_profile_line())
        )
        # the table of the rabbet runs to the left: the line is descending
        m = self.model(
            grid.replace("spacing = 100.0", "origin = 200.0\nspacing = -100.0")
        )
        xs = [x for x, _ in m.rabbet_profile_line()]
        self.assertEqual(sorted(xs, reverse=True), xs)

    def test_bad_rabbet_extra_points(self):
        for text in (
            '[rabbet]\nheight_row = "Height RL"\nextra_points = 3\n',
            '[rabbet]\nheight_row = "Height RL"\nextra_points = [{ station = "A" }]\n',
            '[rabbet]\nheight_row = "Height RL"\n'
            "extra_points = [{ station = 1, dx = 0, height = 0 }]\n",
            '[rabbet]\nextra_points = [{ station = "A", dx = 0, height = 0 }]\n',
        ):
            with self.assertRaises(ValueError, msg=text):
                self.model(text)
        m = self.model(
            self.GRID.replace(
                "siding = 60.0\n",
                'siding = 60.0\nextra_points = [{ station = "X", dx = 0, height = 0 }]\n',
            )
        )
        with self.assertRaises(ValueError):
            m.rabbet_profile_line()

    def test_rabbet_extra_points_in_the_plan_view(self):
        """with a siding: a constant half-breadth over the x of the profile
        line, the extra points included"""
        grid = self.GRID.replace(
            "siding = 60.0\n",
            'siding = 60.0\nextra_points = [{ station = "C", dx = 40.0, height = 9.0 }]\n',
        )
        m = self.model(grid)
        self.assertEqual(
            [(100, -470), (200, -470), (240, -470)], self.mm(m.rabbet_plan_line())
        )

    def test_rabbet_extra_points_with_a_breadth_row(self):
        """the half-breadth: given, else that of the nearest x of the row"""
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C\nHeight Sheer,100,100,100\nBreadth Sheer,300,300,300\n"
                "Height RL,,20,30\nBreadth RL,,5,8\n"
            )
        grid = (
            '[table]\nunit = "mm"\n[stations]\nspacing = 100.0\n'
            "[sheet]\ny_origins = [0, -500]\n"
            '[rabbet]\nheight_row = "Height RL"\nbreadth_row = "Breadth RL"\n'
            "extra_points = [\n"
            '  { station = "C", dx = 10.0, height = 40 },\n'
            '  { station = "C", dx = 60.0, height = 50, breadth = 2 },\n'
            '  { station = "B", dx = -10.0, height = 10 },\n'
            "]\n"
        )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(grid)
        m = table_of_offsets.Model(csv)
        # no base_offset: the plan line is the breadth values; the nearest x
        # of the row: 8 at C (x = 210), 5 at B (x = 90)
        self.assertEqual(
            [(90, 5), (100, 5), (200, 8), (210, 8), (260, 2)],
            self.mm(m.rabbet_plan_line()),
        )
        self.assertEqual(
            [(90, 10), (100, 20), (200, 30), (210, 40), (260, 50)],
            self.mm(m.rabbet_profile_line()),
        )

    def test_bad_extra_points_breadth(self):
        with self.assertRaises(ValueError):
            self.model(
                '[rabbet]\nheight_row = "Height RL"\n'
                'extra_points = [{ station = "A", dx = 0, height = 0, breadth = "x" }]\n'
            )
        with self.assertRaises(ValueError):
            self.model(
                '[rabbet]\nheight_row = "Height RL"\n'
                'extra_points = [{ station = "A", dx = 0, height = 0, width = 1 }]\n'
            )

    def test_rabbet_extra_point_from_table_rows(self):
        """the same as the sheer point of a station: rows instead of numbers"""
        grid = self.GRID.replace(
            "siding = 60.0\n",
            "siding = 60.0\nextra_points = [\n"
            '  { station = "A", height_row = "Height Sheer", breadth_row = "Breadth Sheer" },\n'
            "]\n",
        )
        m = self.model(grid)
        self.assertEqual(
            [(0, 100), (100, 20), (200, 30)], self.mm(m.rabbet_profile_line())
        )
        # the plan line has the siding: the point is on it, the x is the point
        self.assertEqual(3, len(m.rabbet_plan_line()))
        self.assertEqual(0, round(m.rabbet_plan_line()[0][0]))

    def test_bad_extra_point_rows(self):
        base = '[rabbet]\nheight_row = "Height RL"\nextra_points = [%s]\n'
        for point in (
            '{ station = "A" }',
            '{ station = "A", height = 1, height_row = "Height Sheer" }',
            '{ station = "A", height = 1, breadth = 1, breadth_row = "Breadth Sheer" }',
            '{ station = "A", height_row = 3 }',
        ):
            with self.assertRaises(ValueError, msg=point):
                self.model(base % point)
        # an empty cell of the row at the station
        m = self.model(
            self.GRID.replace(
                "siding = 60.0\n",
                'siding = 60.0\nextra_points = [{ station = "A", height_row = "Height RL" }]\n',
            )
        )
        with self.assertRaises(ValueError):
            m.rabbet_profile_line()


class Test_RabbetExtraPointsInViews(unittest.TestCase):
    """the extra points of the rabbet line in the plan and body views"""

    MM = 1.0  # the model works in mm

    def model(self, sides_unused=None):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C\nHeight Sheer,100,100,100\nBreadth Sheer,300,300,300\n"
                "Height RL,50,20,30\nBreadth RL,5,5,5\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\nbow_station = "C"\n'
                "[stations]\nspacing = 100.0\n[sheet]\ny_origins = [0, -500]\n"
                '[rabbet]\nheight_row = "Height RL"\nbreadth_row = "Breadth RL"\n'
                "extra_points = [\n"
                '  { station = "C", dx = 50.0, height = 60, breadth = 4 },\n'
                '  { station = "A", dx = -50.0, height = 70, breadth = 3 },\n'
                "]\n"
            )
        return table_of_offsets.Model(csv)

    def mm(self, pts):
        return [tuple(round(c / self.MM) for c in p) for p in pts]

    def test_body_plan(self):
        m = self.model()
        body = [("Breadth Sheer", "Height Sheer")]
        lines = m.loft_body_lines(body, "raw", sides="split")
        # raw: the centerline is at x = 0; B is the widest (first of equals);
        # C is forward (the bow), A is aft: the extra point at x = 250 is
        # forward (right), the one at x = -50 is aft (left)
        self.assertEqual(
            [(4, 60, "E1"), (-3, 70, "E2")],
            [
                (round(x / self.MM), round(y / self.MM), n)
                for x, y, n in lines.extra_points
            ],
        )
        # they are on the rabbet line of the body plan
        pts = [self.mm(p) for p in lines.rabbet]
        self.assertTrue(any((4, 60) in p for p in pts))
        self.assertTrue(any((-3, 70) in p for p in pts))

    def test_half(self):
        m = self.model()
        lines = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        self.assertEqual(2, len(lines.extra_points))
        self.assertEqual(
            [(4, 60), (3, 70)],
            [
                (round(x / self.MM), round(y / self.MM))
                for x, y, _ in lines.extra_points
            ],
        )

    def test_plot_marks_the_points(self):
        class Dxf:
            def __init__(self):
                self.circles, self.texts, self.lines = [], [], []
                self.layers = []

            def add_red_polyline(self, line):
                self.lines.append(line)

            def add_circle(self, center, radius, layer="red"):
                self.circles.append(center)
                self.layers.append(layer)

            def text(self, xy, txt, layer="text", **kw):
                self.texts.append(txt)
                self.layers.append(layer)

        m = self.model()
        dxf = Dxf()
        m.plot_keel_and_rabbet(dxf)
        # two points in the profile and two in the plan view
        self.assertEqual(4, len(dxf.circles))
        self.assertEqual(["E1", "E1", "E2", "E2"], dxf.texts)
        # the markers and the labels are in their own layer
        self.assertEqual({table_of_offsets.EXTRA_POINT_LAYER}, set(dxf.layers))
        dxf = Dxf()
        m.plot_keel_and_rabbet(dxf, extra_points=False)
        self.assertEqual([], dxf.circles)
        dxf = Dxf()
        lines = m.loft_body_lines([("Breadth Sheer", "Height Sheer")], "raw")
        m.plot_body_lines(dxf, lines)
        self.assertEqual(2, len(dxf.circles))


class Test_ChineLine(unittest.TestCase):
    MM = 1.0  # the model works in mm

    def model(self, chine=True):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C,D\nHeight Sheer,100,100,100,100\n"
                "Breadth Sheer,300,300,300,300\n"
                "Height Chine,,40,45,\nBreadth Chine,,200,250,\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\nbow_station = "D"\n[stations]\nspacing = 100.0\n'
            )
            if chine:
                f.write(
                    '[chine]\nheight_row = "Height Chine"\nbreadth_row = "Breadth Chine"\n'
                )
        return table_of_offsets.Model(csv)

    def test_chine_body_point(self):
        self.assertEqual(
            ("Breadth Chine", "Height Chine"), self.model().chine_body_point()
        )
        self.assertIsNone(self.model(False).chine_body_point())

    def test_chine_line_in_the_body_plan(self):
        m = self.model()
        body = [("Breadth Sheer", "Height Sheer")]
        lines = m.loft_body_lines(body, "raw", sides="half")
        # B and C have the chine; it is a point of their body lines
        chine = [
            [(round(x / self.MM), round(y / self.MM)) for x, y in p]
            for p in lines.chine
        ]
        self.assertEqual([[(200, 40), (250, 45)]], chine)
        for st, pt in (("B", (200, 40)), ("C", (250, 45))):
            self.assertIn(
                pt,
                [(round(x / self.MM), round(y / self.MM)) for x, y in lines[st][0]],
            )
        self.assertEqual(
            chine,
            [
                [(round(x / self.MM), round(y / self.MM)) for x, y in p]
                for p in m.body_chine_polylines(lines)
            ],
        )
        # no chine: no line, nothing added
        self.assertEqual([], list(self.model(False).loft_body_lines(body, "raw").chine))

    def test_chine_is_drawn(self):
        class Dxf:
            def __init__(self):
                self.lines = []

            def add_red_polyline(self, line):
                self.lines.append(line)

            def text(self, *a, **kw):
                pass

        m = self.model()
        lines = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        dxf = Dxf()
        m.plot_body_lines(dxf, lines, chine=False)
        n = len(dxf.lines)
        dxf = Dxf()
        m.plot_body_lines(dxf, lines)
        self.assertEqual(n + 1, len(dxf.lines))

    def test_bad_chine(self):
        for text in (
            '[chine]\nheight_row = "Height Chine"\n',
            '[chine]\nbreadth_row = "Breadth Chine"\n',
            '[chine]\nheight_row = 3\nbreadth_row = "Breadth Chine"\n',
        ):
            d = tempfile.mkdtemp()
            csv = os.path.join(d, "t.csv")
            with open(csv, "w") as f:
                f.write("#,A\nSheer,1\n")
            with open(os.path.join(d, "t.grid"), "w") as f:
                f.write(text)
            with self.assertRaises(ValueError, msg=text):
                table_of_offsets.Model(csv)


class Test_ExtraPointsOfTheKeel(unittest.TestCase):
    """extra_points is not rabbet specific: here the keel line is only
    extra points"""

    MM = 1.0  # the model works in mm

    def model(self, keel):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C,D\nHeight Sheer,100,100,100,100\n"
                "Breadth Sheer,300,300,300,300\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\nbow_station = "D"\n[stations]\nspacing = 100.0\n'
                "[sheet]\ny_origins = [0, -500]\n" + keel
            )
        return table_of_offsets.Model(csv)

    KEEL = (
        "[keel]\nsiding = 40.0\nextra_points = [\n"
        '  { station = "A", dx = 50.0, height = 10 },\n'
        '  { station = "C", dx = 20.0, height = 30, breadth = 5 },\n]\n'
    )

    def mm(self, pts):
        return [tuple(round(c / self.MM) for c in p) for p in pts]

    def test_the_line_is_the_extra_points(self):
        m = self.model(self.KEEL)
        # the half-breadth: given, else half the siding
        self.assertEqual([(50, 10, 20), (220, 30, 5)], self.mm(m.keel_points()))
        self.assertEqual([(50, 10), (220, 30)], self.mm(m.keel_profile_line()))
        self.assertEqual([(50, -480), (220, -495)], self.mm(m.keel_plan_line()))
        self.assertIsNone(m.keel_point_at("A"))  # x = 0, before the line
        x, y = m.keel_point_at("B")  # x = 100: 50/170 of the way
        self.assertAlmostEqual((20 + 50 / 170 * (5 - 20)) * self.MM, x)
        self.assertAlmostEqual((10 + 50 / 170 * 20) * self.MM, y)
        self.assertIsNone(m.keel_point_at("D"))

    def test_order_of_the_file_without_a_line(self):
        """no x ordering: the shape of a stem can go back"""
        m = self.model(
            "[keel]\nextra_points = [\n"
            '  { station = "C", height = 30 },\n  { station = "A", height = 10 },\n]\n'
        )
        self.assertEqual([(200, 30), (0, 10)], self.mm(m.keel_profile_line()))

    def test_merged_with_the_line(self):
        m = self.model(
            '[keel]\nfrom = { station = "A", height = 0 }\n'
            'to = { station = "D", height = 0 }\n'
            'extra_points = [{ station = "B", dx = 10.0, height = 7 }]\n'
        )
        self.assertEqual([(0, 0), (110, 7), (300, 0)], self.mm(m.keel_profile_line()))

    def test_in_the_body_plan_and_marked(self):
        m = self.model(self.KEEL)
        lines = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        # K1, the keel points of B and C, K2 (B and C have the keel point)
        keel = [
            [(round(x / self.MM), round(y / self.MM)) for x, y in p] for p in lines.keel
        ]
        self.assertEqual(1, len(keel))
        self.assertEqual((20, 10), keel[0][0])
        self.assertEqual((5, 30), keel[0][-1])
        self.assertEqual(4, len(keel[0]))  # K1, B, C, K2
        self.assertEqual(["K1", "K2"], [label for _, _, label in lines.extra_points])

        class Dxf:
            def __init__(self):
                self.texts = []

            def add_red_polyline(self, line):
                pass

            def add_circle(self, center, radius, layer="red"):
                pass

            def text(self, xy, txt, **kw):
                self.texts.append(txt)

        dxf = Dxf()
        m.plot_keel_and_rabbet(dxf)
        self.assertEqual(["K1", "K1", "K2", "K2"], dxf.texts)

    def test_only_the_known_elements(self):
        """extra_points of an element that has none is an unknown key"""
        with self.assertRaises(ValueError):
            self.model(
                '[chine]\nheight_row = "Height Sheer"\nbreadth_row = "Breadth Sheer"\n'
                'extra_points = [{ station = "A", height = 1 }]\n'
            )

    def test_bad_keel_extra_points(self):
        for text in (
            "[keel]\nextra_points = 3\n",
            '[keel]\nextra_points = [{ station = "A" }]\n',
            '[keel]\nextra_points = [{ station = "A", height = 1, bogus = 2 }]\n',
        ):
            with self.assertRaises(ValueError, msg=text):
                self.model(text)
        m = self.model('[keel]\nextra_points = [{ station = "X", height = 1 }]\n')
        with self.assertRaises(ValueError):
            m.keel_points()


class Test_ExtraPointsLayer(unittest.TestCase):
    """the circles and the labels of the extra points are in their own layer
    of the .dxf file"""

    def test_dxf_layer(self):
        import ezdxf

        d = tempfile.mkdtemp()
        out = os.path.join(d, "out.dxf")
        with table_of_offsets.DXF(out) as dxf:
            dxf.add_red_polyline([(0, 0), (1, 1)])
            dxf.text((0, 0), "station")
            dxf.add_circle((5, 5), 1.0, layer=table_of_offsets.EXTRA_POINT_LAYER)
            dxf.text((6, 6), "E1", layer=table_of_offsets.EXTRA_POINT_LAYER)
        doc = ezdxf.readfile(out)
        self.assertIn(table_of_offsets.EXTRA_POINT_LAYER, doc.layers)
        msp = doc.modelspace()
        self.assertEqual(
            [table_of_offsets.EXTRA_POINT_LAYER],
            [e.dxf.layer for e in msp.query("CIRCLE")],
        )
        self.assertEqual(
            {"station": "text", "E1": table_of_offsets.EXTRA_POINT_LAYER},
            {e.dxf.text: e.dxf.layer for e in msp.query("TEXT")},
        )
        self.assertEqual(["red"], [e.dxf.layer for e in msp.query("POLYLINE")])


class Test_ExtraPointEdge(unittest.TestCase):
    """the boolean attribute edge of an extra point: off by default"""

    def model(self, points):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write("#,A,B\nHeight Sheer,1,1\n")
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write("[table]\nunit = 'ftin'\n[keel]\nextra_points = [%s]\n" % points)
        return table_of_offsets.Model(csv)

    def test_default_is_off(self):
        m = self.model(
            '{ station = "A", height = 1 },'
            '{ station = "B", height = 2, edge = true },'
            '{ station = "B", height = 3, edge = false }'
        )
        self.assertEqual([False, True, False], m.extra_point_edges("keel"))
        self.assertEqual([], m.extra_point_edges("rabbet"))
        self.assertEqual(3, len(m.extra_points("keel")))

    def test_edge_must_be_boolean(self):
        for value in ('"on"', "1", '"true"'):
            with self.assertRaises(ValueError, msg=value):
                self.model('{ station = "A", height = 1, edge = %s }' % value)


class Test_EdgesInTheOrthogonalViews(unittest.TestCase):
    """an extra point with edge = true is seen in the profile view; its edge
    is seen in the plan view and in the body plan"""

    MM = 1.0  # the model works in mm

    def model(self):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B,C,D\nHeight Sheer,100,100,100,100\n"
                "Breadth Sheer,300,300,300,300\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\nbow_station = "D"\n[stations]\nspacing = 100.0\n'
                "[sheet]\ny_origins = [0, -500]\n[keel]\nsiding = 40.0\n"
                "extra_points = [\n"
                '  { station = "A", dx = 50.0, height = 10, edge = true },\n'
                '  { station = "C", dx = 20.0, height = 30, breadth = 5 },\n'
                '  { station = "D", height = 50, edge = true },\n]\n'
            )
        return table_of_offsets.Model(csv)

    def mm(self, lines):
        return [[tuple(round(c / self.MM) for c in p) for p in e] for e in lines]

    def test_plan(self):
        # from the plan centerline to the half-breadth
        self.assertEqual(
            [[(50, -500), (50, -480)], [(300, -500), (300, -480)]],
            self.mm(self.model().edge_plan_lines()),
        )

    def test_body_plan(self):
        m = self.model()
        half = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="half"
        )
        self.assertEqual(
            [[(0, 10), (20, 10)], [(0, 50), (20, 50)]], self.mm(half.edges)
        )
        both = m.loft_body_lines(
            [("Breadth Sheer", "Height Sheer")], "raw", sides="both"
        )
        self.assertEqual(
            [[(-20, 10), (20, 10)], [(-20, 50), (20, 50)]], self.mm(both.edges)
        )

    def test_no_edge_by_default(self):
        m = self.model()
        m._meta["keel"]["extra_points"] = [
            {"station": "A", "height": 10.0},
        ]
        self.assertEqual([], m.edge_plan_lines())


class Test_ExtraPointHeightRowIsAWaterline(unittest.TestCase):
    """height_row naming a waterline: the height of the waterline, not the
    value of the row of the same name (its half-breadths, drawn in the plan
    view below the profile view by base_offset)"""

    class Model(table_of_offsets.Model):
        def base_offset(self, line_name):
            return -100.0 if line_name in ("DWL", "8 LL") else 0.0

    def model(self):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,A,B\nHeight RL,0-6-0,0-6-0\nDWL,0-5-6,0-5-6\n8 LL,0-10-4,0-10-4\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                "[table]\nunit = 'ftin'\n[sheet]\ny_origins = [0, -100]\n"
                "[waterlines]\nDWL = { height = 0.0 }\n'8 LL' = { height = 8.0 }\n"
                "[rabbet]\nheight_row = 'Height RL'\n"
                "extra_points = [\n"
                "  { station = 'A', dx = 9.0, height_row = 'DWL', breadth = 3.5 },\n"
                "  { station = 'A', dx = 15.0, height_row = '8 LL', breadth = 3.5 },\n"
                "  { station = 'A', dx = 20.0, height_row = 'Height RL', breadth = 3.5 },\n"
                "]\n"
            )
        return self.Model(csv)

    def test_heights(self):
        points = self.model().extra_points("rabbet")
        self.assertEqual([0.0, 8.0, 6.0], [h for _, h, _ in points])
        self.assertEqual([9.0, 15.0, 20.0], [x for x, _, _ in points])


class Test_KeelRows(unittest.TestCase):
    """[keel] height_row and breadth_row, like [rabbet]"""

    def model(self, keel, extra=""):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write(
                "#,FP,1,2,3\nProfile,,2-0-0,1-0-0,0-6-0\n"
                "Keel Breadth,,0-3-0,0-2-0,\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                "[table]\nunit = 'ftin'\n[stations]\nspacing = -24\norigin = 72\n"
                "[sheet]\ny_origins = [0, -100]\n[keel]\n%s\n%s" % (keel, extra)
            )
        return table_of_offsets.Model(csv)

    def test_row_with_a_siding(self):
        m = self.model('height_row = "Profile"\nsiding = 4.0\n')
        # FP has no cell; the x of the stations 1, 2, 3: 48, 24, 0
        self.assertEqual(
            [(48.0, 24.0, 2.0), (24.0, 12.0, 2.0), (0.0, 6.0, 2.0)],
            m.keel_points(),
        )
        self.assertEqual([(x, y) for x, y, _ in m.keel_points()], m.keel_profile_line())
        self.assertEqual(
            [(48.0, -98.0), (24.0, -98.0), (0.0, -98.0)], m.keel_plan_line()
        )

    def test_breadth_row(self):
        """the breadth of the row at the same x, else the nearest one"""
        m = self.model('height_row = "Profile"\nbreadth_row = "Keel Breadth"\n')
        self.assertEqual(
            [(48.0, 24.0, 3.0), (24.0, 12.0, 2.0), (0.0, 6.0, 2.0)],
            m.keel_points(),
        )

    def test_extra_points_are_merged_by_x(self):
        m = self.model(
            'height_row = "Profile"\nbreadth_row = "Keel Breadth"\n',
            "extra_points = [\n"
            '  { station = "1", dx = 6.0, height = 20, breadth = 1 },\n'
            '  { station = "2", dx = 6.0, height = 9, breadth = 1 },\n'
            "]\n",
        )
        # the extra points are at x = 54 and 30
        self.assertEqual(
            [54.0, 48.0, 30.0, 24.0, 0.0], [x for x, _, _ in m.keel_points()]
        )

    def test_the_section_goes_down_to_the_row(self):
        m = self.model('height_row = "Profile"\nsiding = 4.0\n')
        self.assertEqual((2.0, 12.0), m.keel_point_at("2"))
        # between two stations: interpolated
        self.assertIsNone(m.keel_point_at("FP"))

    def test_errors(self):
        for keel in ('breadth_row = "x"', "height_row = 1", 'height_row = ""'):
            with self.assertRaises(ValueError, msg=keel):
                self.model(keel)
