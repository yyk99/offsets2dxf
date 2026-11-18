"""Project 181: model for sample_data_too/offset_table_181.csv.

Heights (Sheer, the buttocks, Rabbet, Profile) are measured from the DWL, positive up. Half-breadths
are the "Sheerline", "... LL", "... DL" and "Rabbet Line" rows. The diagonals D1-D3 are given
(``diagonals_positions``, heights above the DWL). The Profile (keel line) has no
half-breadth in the table: its body line points use that of the "Rabbet Line".

Run: ``python3 project181.py [--out-dir DIR] [--output-units UNIT]`` -> writes, into ./out (in the
current directory) or DIR, test_project181.dxf (everything, body lines in the middle of the profile
view) and test_project181_body.dxf (body lines only) and
test_project181_station1.dxf, _station4.dxf, _station5.dxf and _station8.dxf (the body line
of the station with every point labelled).
"""

import context
from context import table_of_offsets

import os


#
# Model implementation specific for the sample data
#
class Project181(table_of_offsets.Model):
    def __init__(self):
        super().__init__(
            os.path.join(
                os.path.dirname(__file__), "../sample_data_too/offset_table_181.csv"
            )
        )
        # fmt: off
        self.set_under_waterline(
            { 
                '36" Buttock': [ "5" ],
                '24" Buttock': [ "3", "4", "5", "6", "7" ],
                '12" Buttock': [ "2", "3", "4", "5", "6", "7" ],
                'Rabbet': [ "1", "2", "3", "4", "5", "6", "7", "8" ],
                'Profile': [ "1", "2", "3", "4", "5", "6", "7" ],
            }
        )
        # fmt: on
        self.set_bow_station("FP")  # the stem; the stern (AP) is at x = 0
        self._y0 = 0.0
        self._y1 = -100.0
        pass

    def station_positions(self):
        """Return a dictionary of station positions"""
        station_positions = {}
        for c in self._too.columns:
            if c == "#":
                pass
            elif c == "AP":
                station_positions[c] = 0.0
            elif c == "FP":
                station_positions[c] = 24 * 9
            else:
                assert c.isdecimal()
                station_positions[c] = (9 - int(c)) * 24  # 1' == 12" (inches)
        return station_positions

    def waterlines_positions(self):
        return {
            '24" LL': 24.0,
            '16" LL': 16.0,
            '8" LL': 8.0,
            "DWL": 0.0,
            '8" DL': -8,
            '16" DL': -16.0,
            '24" DL': -24.0,
        }

    def buttocks_positions(self):
        return {
            '36" Buttock': 36.0,
            '24" Buttock': 24.0,
            '12" Buttock': 12.0,
        }

    def base_offset(self, line_name):
        if line_name in [
            "Sheerline",
            '24" LL',
            '16" LL',
            '8" LL',
            "DWL",
            '8" DL',
            '16" DL',
            "Rabbet Line",
        ]:
            return self._y1
        return self._y0

    def drawing_area_vertical_borders(self):
        """The station lines run down below the diagonals of the plan view
        (the lowest, D3, is at about -142)"""
        return (-150.0, 120.0)

    def grid_y_origins(self):
        return [self._y0, self._y1]

    def diagonals_positions(self):
        """{name: (y0, x1, y1)}, inches above the DWL: the line from (0, y0)
        through (x1, y1). Given: D1 from (0, 0) through (24, -24), D2 from
        (0, 16) through (24, -8) and D3 from (0, 24) through (36, 8)."""
        return {
            "D1": (0.0, 24.0, -24.0),
            "D2": (16.0, 24.0, -8.0),
            "D3": (24.0, 36.0, 8.0),
        }

    def diagonal_extension(self):
        """The diagonals reach 6" beyond the farthest hull point"""
        return 6.0

    def rabbet_body_point(self):
        return ("Rabbet Line", "Rabbet")

    def keel_body_point(self):
        """The profile (keel) line: the table has the heights only, the
        half-breadth is that of the rabbet line"""
        return ("Rabbet Line", "Profile")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        and the diagonals (``loft_body_lines`` adds them): a string is a table
        row, a number is inches."""
        return [
            ("Sheerline", "Sheer"),
            ("Rabbet Line", "Rabbet"),
            ("Rabbet Line", "Profile"),
            # buttocks: height from the table, breadth is the buttock
            (36.0, '36" Buttock'),
            (24.0, '24" Buttock'),
            (12.0, '12" Buttock'),
        ]

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: polyline} with the body plan line of every station.

        Points are (half-breadth, height above the DWL) in inches.
        """
        return self.loft_body_lines(
            self.body_points(), placement, sides=sides, bow_station=bow_station
        )

    def save_station_as(self, filename_dxf: str, station: str = "1"):
        """Save the body line of one station for checking the data: every point
        is labelled with the table rows its coordinates come from."""
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_annotated_body_line(
                dxf, station, self.body_points(), point_text_height=1.0
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

    def save_model_as(self, filename_dxf: str):
        body_lines = self.body_lines()
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf)

            dxf.add_red_polyline(self.loft_line_n_sorted(0))
            dxf.add_red_polyline(self.loft_line_n_sorted(1))
            dxf.add_red_polyline(self.loft_line_n_sorted(2))
            dxf.add_red_polyline(self.loft_line_n_sorted(3))
            dxf.add_red_polyline(self.loft_line_n_sorted(4))
            dxf.add_red_polyline(self.loft_line_n_sorted(5))  # Profile (keel)
            #
            dxf.add_red_polyline(self.loft_line_n_sorted(6))
            # waterlines: 24" LL, 16" LL, 8" LL, DWL, 8" DL, 16" DL
            for n in range(7, 13):
                dxf.add_red_polyline(self.loft_line_n_sorted(n))

            # the diagonals in the plan view, below the plan centerline
            self.plot_diagonal_plan_lines(dxf)

            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir
    proj = Project181()
    proj.set_output_unit(args.output_units)

    print(proj.station_positions())

    filename = os.path.join(out_dir, "test_project181.dxf")
    proj.save_model_as(filename)
    print("Saved as:", filename)

    filename = os.path.join(out_dir, "test_project181_body.dxf")
    proj.save_body_lines_as(filename)
    print("Saved as:", filename)

    # one station, every point labelled with the source of its coordinates
    for station in ("1", "4", "5", "8"):
        filename = os.path.join(out_dir, "test_project181_station%s.dxf" % station)
        proj.save_station_as(filename, station)
        print("Saved as:", filename)

# end of file
