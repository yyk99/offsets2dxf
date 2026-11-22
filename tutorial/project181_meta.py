"""Project 181 with the grid from a meta data file.

The same model as project181.py (see there for the table layout), but
everything the grid file can say is read from
sample_data_too/offset_table_181.meta: the stations, the waterlines, the
buttocks, the diagonals D1-D3, the rabbet rows and the sheet layout. What is
left in this file: the stations where a line is under the waterline, the
keel (Profile) point, the diagonal extension and what to draw.

The output is that of project181.py (the rabbet line is also drawn in the
plan view, from the grid file), with the names tutorial_project181_meta*.dxf.

Run: ``python3 project181_meta.py [--out-dir DIR] [--output-units UNIT]`` ->
writes, into ./out (in the current directory) or DIR,
tutorial_project181_meta.dxf (everything, body lines in the middle of the
profile view), tutorial_project181_meta_body.dxf (body lines only) and
tutorial_project181_meta_station1.dxf, _station4.dxf, _station5.dxf and
_station8.dxf (the body line of the station with every point labelled).
"""

import context
from context import table_of_offsets

import os


class Project181Meta(table_of_offsets.Model):
    def __init__(self):
        # the grid is read from offset_table_181.meta next to the CSV
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

    def base_offset(self, line_name):
        """The half-breadths are drawn above the centerline of the plan view."""
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
            return self.plan_centerline_y()
        return 0.0

    def diagonal_extension(self):
        """The diagonals reach 6" beyond the farthest hull point"""
        return 6.0

    def keel_body_point(self):
        """The profile (keel) line: the table has the heights only, the
        half-breadth is that of the rabbet line"""
        return ("Rabbet Line", "Profile")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        and the diagonals (``loft_body_lines`` adds them): a string is a table
        row, a number is inches. The rabbet is from the grid file; it is
        listed so that the annotated station has it too (``loft_body_lines``
        does not add it twice)."""
        return [
            ("Sheerline", "Sheer"),
            self.rabbet_body_point(),
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

            # profile view
            for name in [
                "Sheer",
                '36" Buttock',
                '24" Buttock',
                '12" Buttock',
                "Profile",  # the keel
            ]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # plan view
            for name in [
                "Sheerline",
                '24" LL',
                '16" LL',
                '8" LL',
                "DWL",
                '8" DL',
                '16" DL',
            ]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # the rabbet, in the profile and plan views, as the grid file
            # gives it ([rabbet])
            self.plot_keel_and_rabbet(dxf)

            # the diagonals in the plan view, below the plan centerline
            self.plot_diagonal_plan_lines(dxf)

            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir
    proj = Project181Meta()
    proj.set_output_unit(args.output_units)

    print(proj.station_positions())

    filename = os.path.join(out_dir, "tutorial_project181_meta.dxf")
    proj.save_model_as(filename)
    print("Saved as:", filename)

    filename = os.path.join(out_dir, "tutorial_project181_meta_body.dxf")
    proj.save_body_lines_as(filename)
    print("Saved as:", filename)

    # one station, every point labelled with the source of its coordinates
    for station in ("1", "4", "5", "8"):
        filename = os.path.join(
            out_dir, "tutorial_project181_meta_station%s.dxf" % station
        )
        proj.save_station_as(filename, station)
        print("Saved as:", filename)

# end of file
