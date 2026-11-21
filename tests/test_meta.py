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
            self.assertAlmostEqual(v / 25.4, actual_inches[k], msg=k)

    def test_positions(self):
        model = self.model(
            "[table]\nunit = 'mm'\n"
            "[stations.positions]\nFP = 3000\n'1A' = 2500.5\n"
            "'1' = 2000\n'2' = 1000\nT = 0\n"
        )
        # the lengths of the file are in millimetres, the model has inches
        self.assertMm(
            {"FP": 3000.0, "1A": 2500.5, "1": 2000.0, "2": 1000.0, "T": 0.0},
            model.station_positions(),
        )
        self.assertAlmostEqual(1240 / 25.4, model.breadth_at("1A", "Sheer"))

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
        """no meta data: the n-th station is at n * 12 inches, whatever the
        names"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.csv")
            with open(path, "w") as f:
                f.write(self.CSV)
            model = table_of_offsets.Model(path, unit="mm")
            self.assertEqual(
                {"FP": 0, "1A": 12, "1": 24, "2": 36, "T": 48},
                model.station_positions(),
            )

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
        model = table_of_offsets.Model(CSV, meta=False)
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
            self.assertAlmostEqual(5 / 25.4, model.station_positions()["B"])
            self.assertEqual("mm", model.offsets_unit())
            other = table_of_offsets.Model(csv, meta=False)
            self.assertEqual("ftin", other.offsets_unit())

    def test_explicit_path_and_missing_file(self):
        table_of_offsets.Model(CSV, meta=META)
        with self.assertRaises(FileNotFoundError):
            table_of_offsets.Model(CSV, meta="nope.meta")


if __name__ == "__main__":
    unittest.main()


class Test_MetaLengthsInTableUnit(unittest.TestCase):
    def test_mm_lengths_are_converted_to_inches(self):
        with tempfile.TemporaryDirectory() as d:
            csv = os.path.join(d, "t.csv")
            with open(csv, "w") as f:
                f.write("#,1,2\nHeight Sheer,100,200\n")
            with open(os.path.join(d, "t.grid"), "w") as f:
                f.write(
                    '[table]\nunit = "mm"\n[stations]\nspacing = 254.0\n'
                    "[buttocks]\nB1 = 508.0\n"
                    '[waterlines]\nWL = { height = 25.4 }\n'
                )
            m = table_of_offsets.Model(csv)
            self.assertAlmostEqual(m.station_positions()["2"], 10.0)
            self.assertAlmostEqual(m.buttocks_positions()["B1"], 20.0)
            self.assertAlmostEqual(m.waterlines_positions()["WL"], 1.0)


class Test_Siding(unittest.TestCase):
    def model(self, text):
        d = tempfile.mkdtemp()
        csv = os.path.join(d, "t.csv")
        with open(csv, "w") as f:
            f.write("#,1\nHeight Sheer,100\n")
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(text)
        return table_of_offsets.Model(csv)

    def test_siding_in_table_unit(self):
        m = self.model('[table]\nunit = "mm"\n[keel]\nsiding = 50.8\n[rabbet]\nsiding = 25.4\n')
        self.assertAlmostEqual(2.0, m.siding("keel"))
        self.assertAlmostEqual(1.0, m.siding("rabbet"))
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
            f.write(text)
        return table_of_offsets.Model(csv)

    def test_keel_line(self):
        m = self.model(
            '[table]\nunit = "mm"\n[stations]\nspacing = 254.0\n'
            '[keel]\nfrom = { station = "B", height = 25.4 }\n'
            'to = { station = "C", height = 0 }\n'
        )
        (x0, y0), (x1, y1) = m.keel_line()
        self.assertAlmostEqual(10.0, x0)
        self.assertAlmostEqual(1.0, y0)
        self.assertAlmostEqual(20.0, x1)
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
            f.write(
                "#,A,B,C\nHeight Sheer,100,100,100\n"
                "Breadth Sheer,300,300,300\n"
            )
        with open(os.path.join(d, "t.grid"), "w") as f:
            f.write(
                '[table]\nunit = "mm"\n[stations]\nspacing = 100.0\n'
                '[keel]\nfrom = { station = "B", height = 0 }\n'
                'to = { station = "C", height = 10.0 }\nsiding = 40.0\n'
            )
        m = table_of_offsets.Model(csv)
        mm = 1 / 25.4
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
    MM = 1 / 25.4

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
        self.assertIn((30, 30), [(round(x / self.MM), round(y / self.MM)) for x, y in lines["C"][0]])

    def test_nothing_in_the_file(self):
        m = self.model("[table]\nunit = 'mm'\n")
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
