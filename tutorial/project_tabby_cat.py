"""Tabby Cat: model of sample_data/tabby_cat/offset_table.csv

Source: the lines plan "Teoreticheskiy chertezh" with the table of the offsets
("Tablitsa plazovykh ordinat, mm"), see sample_data/tabby_cat/. The table is
in millimetres (``unit="mm"``); the model works in inches.

Table layout: stations ``1`` .. ``12``; rows named ``Height ...`` are heights
above the baseline (Sheer, Buttock 1-4, Rabbet, Keel), rows named
``Breadth ...`` are half-breadths from the centerline (Sheer, WL I-VIII,
Rabbet, Keel; the last one is assumed by the designer). The cells marked "-" in the source are empty. The diagonals D1 and D2 (rows
``Diagonal D1``, ``Diagonal D2``) are distances along the lines of
``DIAGONALS_MM`` from the centerline, see ``diagonals_positions``.

Known about the hull (not in the table; confirmed):

- the stations are 510 mm apart (the drawing: 510, 510, 305 near the stem); the bow is station 1 and the stern, station
  12, is at x = 0 (the stem is 305 mm ahead of the station 1 and the drawing
  origin, "OL", is there; it is not used);
- the heights of the waterlines above the baseline (given): WL I 600, WL II
  700, WL III 800, WL IV 900, WL V (the design waterline, KVL) 1000, WL VI
  1150, WL VII 1300, WL VIII 1450 mm;
- the buttocks 1-4 are 300 mm apart (300, 600, 900, 1200 mm from the
  centerline), as confirmed; the sections through the waterline points and
  the buttock heights agree with it, e.g. at station 6.

Run: ``python3 project_tabby_cat.py [--out-dir DIR] [--output-units UNIT]``
writes, into ./out (in the current directory) or DIR,
test_project_tabby_cat.dxf (everything), test_project_tabby_cat_body_right.dxf
(body plan to the right of the profile view),
test_project_tabby_cat_body_split.dxf (aft/forward halves),
test_project_tabby_cat_body.dxf (body lines only) and
test_project_tabby_cat_station6.dxf (the body line of the station 6 with the
table rows the coordinates of every point come from).
"""

import context
from context import table_of_offsets

import os

MM = 1.0 / 25.4  # inches in a millimetre

STATION_DISTANCE_MM = 510.0
BUTTOCK_DISTANCE_MM = 300.0
DWL_NUMBER = 5  # the design waterline is "WL V" of the table
# heights of the waterlines WL 1 .. WL 8 above the baseline, mm
WATERLINE_HEIGHTS_MM = [600, 700, 800, 900, 1000, 1150, 1300, 1450]
# the diagonals D1 and D2 of the body plan: (y0, x1, y1), mm. The lines run
# from the centerline at y0 above the baseline to the point (x1, y1), as
# dimensioned in the construction midsection (konstruktivnyy_midel-
# shpangout_2.jpg): both start 1700 mm above the baseline; D1 ends on the
# baseline 1100 mm from the centerline, D2 ends 1850 mm from the centerline on
# the design waterline (1000 mm).
DIAGONALS_MM = {"D1": (1700, 1100, 0), "D2": (1700, 1850, 1000)}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


class ProjectTabbyCat(table_of_offsets.Model):
    def __init__(self):
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data/tabby_cat/offset_table.csv",
            ),
            unit="mm",
        )
        self.set_bow_station("1")  # the stern (station 12) is at x = 0
        # the plan view is drawn below the profile view
        self._y_plan = -100.0

    def station_positions(self):
        """The stations are 510 mm apart; the stern, station 12, is at x = 0."""
        return {
            c: (12 - int(c)) * STATION_DISTANCE_MM * MM
            for c in self._too.columns
            if c != "#"
        }

    def base_offset(self, line_name: str):
        """The half-breadths are drawn above the centerline of the plan view."""
        if line_name.startswith("Breadth "):
            return self._y_plan
        return 0

    def buttocks_positions(self):
        return {
            "B %d" % n: n * BUTTOCK_DISTANCE_MM * MM for n in range(1, 5)
        }

    def waterline_row(self, name: str) -> str:
        """the half-breadths of "WL n" are in the row "Breadth WL <roman n>";
        DWL is WL V"""
        n = DWL_NUMBER if name == "DWL" else int(name.split()[1])
        return "Breadth WL " + ROMAN[n - 1]

    def waterlines_positions(self):
        """{name: height above the baseline} of the waterlines WL 1 .. WL 8"""
        return {
            ("DWL" if n == DWL_NUMBER else "WL %d" % n): h * MM
            for n, h in enumerate(WATERLINE_HEIGHTS_MM, 1)
        }

    def grid_y_origins(self):
        """the baseline of the profile view, the centerline of the plan view"""
        return [0.0, self._y_plan]

    def drawing_area_vertical_borders(self):
        return (self._y_plan - 20, 110.0)

    def diagonal_row(self, name: str) -> str:
        return "Diagonal " + name

    def diagonals_positions(self):
        """{name: (y0, x1, y1)} of D1 and D2, see ``DIAGONALS_MM``"""
        return {
            name: (y0 * MM, x1 * MM, y1 * MM)
            for name, (y0, x1, y1) in DIAGONALS_MM.items()
        }

    def keel_body_point(self):
        return ("Breadth Keel", "Height Keel")

    def rabbet_body_point(self):
        return ("Breadth Rabbet", "Height Rabbet")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        (``loft_body_lines`` adds them): a string is a table row, a number is
        inches."""
        body_points = [
            ("Breadth Sheer", "Height Sheer"),
            ("Breadth Rabbet", "Height Rabbet"),
            ("Breadth Keel", "Height Keel"),
        ]
        # the waterlines are added by loft_body_lines (waterlines_positions)
        body_points += [
            (offset, "Height Buttock " + name[2:])
            for name, offset in self.buttocks_positions().items()
        ]
        return body_points

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: [polyline, ...]}: the body plan lines.

        Points are (half-breadth, height above the baseline) in inches: the
        sheer, the rabbet, the keel, the four buttocks and the waterlines
        WL 1 - WL 8.
        """
        return self.loft_body_lines(
            self.body_points(), placement, sides=sides, bow_station=bow_station
        )

    def save_body_lines_as(
        self, filename_dxf: str, placement: str = "max_breadth", sides: str = None
    ):
        """Save the body lines and their grid (base line, centerline,
        waterlines, buttocks); no plan/profile lines"""
        with self.open_dxf(filename_dxf) as dxf:
            lines = self.body_lines(placement, sides)
            self.plot_body_plan_grid(dxf, lines)
            self.plot_body_lines(dxf, lines)

    def save_station_as(self, filename_dxf: str, station: str = "6"):
        """Save the body line of one station for checking the data: every point
        is labelled with the table rows its coordinates come from."""
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_annotated_body_line(dxf, station, self.body_points())

    def save_model_as(
        self,
        filename_dxf: str,
        body_placement: str = "max_breadth",
        body_sides: str = None,
    ):
        body_lines = self.body_lines(body_placement, body_sides)
        grid_options = {}
        if body_placement == "right":
            # run the base line through the body plan, draw its centerline
            # and buttocks
            grid_options = self.body_plan_grid_options(body_lines, body_sides)

        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf, **grid_options)

            # profile view
            for name in [
                "Height Buttock 1",
                "Height Buttock 2",
                "Height Buttock 3",
                "Height Buttock 4",
                "Height Keel",
                "Height Rabbet",
                "Height Sheer",
            ]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # plan view
            for name in (
                ["Breadth Keel", "Breadth Rabbet"]
                + ["Breadth WL " + r for r in ROMAN]
                + ["Breadth Sheer"]
            ):
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # the diagonals in the plan view, below its centerline
            self.plot_diagonal_plan_lines(dxf)

            # body plan
            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = ProjectTabbyCat()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("test_project_tabby_cat.dxf"))
    print("Saved as:", out("test_project_tabby_cat.dxf"))
    # the body plan to the right of the profile view, clear of it
    proj.save_model_as(
        out("test_project_tabby_cat_body_right.dxf"), body_placement="right"
    )
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        out("test_project_tabby_cat_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as(out("test_project_tabby_cat_body.dxf"))
    # one station, every point labelled with the source of its coordinates
    proj.save_station_as(out("test_project_tabby_cat_station6.dxf"), "6")
    print("Saved as:", out("test_project_tabby_cat_body.dxf"))

# end of file
