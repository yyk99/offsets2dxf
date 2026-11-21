"""Project 89: model of the sample table (sample_data/offset_table.csv).

Heights (Sheer, B 3', B 2', B 1', Rabbet, Profile) are measured from the LWL,
positive up. Half-breadths are the "1/2w Deck", "WL ..." and "... Plan" rows.
The grid (stations, waterlines, buttocks, diagonals, ghost line, sheet
layout), the bow station and the treatment of the cells with two values
("0-2-0 and 0-3-0": the first one is used) are in the meta data file
``sample_data/offset_table.meta``, which ``Model`` loads.

Body plan sides (``body_sides``): ``"half"``, ``"both"`` (both halves) or
``"split"`` (aft stations on the left, forward on the right). The default is
``"split"`` for the body plan in the middle of the profile view and ``"half"``
for the others.

Body plan placement (``body_placement``): ``"max_breadth"`` (default) puts the
body lines in the middle of the profile view, ``"right"`` puts them to the
right of it.

Run: ``python3 project89.py [--out-dir DIR] [--output-units UNIT]`` writes, into ./out (in the
current directory) or DIR, tutorial_project89.dxf (everything),
tutorial_project89_body_right.dxf (body plan to the right),
tutorial_project89_body_split.dxf (aft/forward halves) and
tutorial_project89_body.dxf (body lines only) and
tutorial_project89_station14.dxf, _station16.dxf and _station18.dxf (the body line
of the station with every point labelled).
"""

import context
from context import table_of_offsets

import os


#
# Model implementation spicific for the sample data
#
class Project89(table_of_offsets.Model):
    def __init__(self):
        super().__init__(
            os.path.join(os.path.dirname(__file__), "../sample_data/offset_table.csv")
        )
        # fmt: off
        self.set_under_waterline(
            {
                "B 3'": [
                    "24", "22", "20", "18", "16", "14", "12",
                ],
                "B 2'": [
                    "26", "24", "22", "20", "18", "16", "14", "12", "10", "8"
                ],
                "B 1'": [
                    "28", "26", "24", "22", "20", "18", "16", "14", "12", "10", "8", "6"
                ],
                "Rabbet": [ 
                    "30", "28", "26", "24", "22", "20", "18",
                    "16", "14", "12", "10",  "8",  "6",  "4",
                ],
                "Profile": [
                    "30", "28", "26", "24", "22", "20", "18",
                    "16", "14", "12", "10",  "8",  "6",  "4",  "2",
                ],
            }
        )
        # fmt: on
        pass

    def base_offset(self, line_name: str):
        if line_name in [
            "1/2w Deck",
            "WL + 2'",
            "WL + 1'",
            'WL + 6"',
            "LWL",
            'WL - 6"',
            "WL - 1'",
            "WL - 2'",
            "WL - 3'",
            "WL - 4'",
            "Rabbet Plan",
            "Profile Plan",
        ]:
            return 10 * 12.0  #
        return 0

    def keel_body_point(self):
        return ("Profile Plan", "Profile")

    def rabbet_body_point(self):
        return ("Rabbet Plan", "Rabbet")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        and the diagonals (``loft_body_lines`` adds them): a string is a table
        row, a number is inches."""
        body_points = [
            ("1/2w Deck", "Sheer"),
            ("Rabbet Plan", "Rabbet"),
            ("Profile Plan", "Profile"),
        ]
        # buttocks: height from the table, breadth is the buttock
        body_points += [(36.0, "B 3'"), (24.0, "B 2'"), (12.0, "B 1'")]
        return body_points

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: polyline} with the body plan line of every station.

        Points are (half-breadth, height above the LWL) in inches.
        """
        body_points = self.body_points()
        return self.loft_body_lines(
            body_points, placement, sides=sides, bow_station=bow_station
        )

    def save_station_as(self, filename_dxf: str, station: str):
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

    def save_model_as(
        self,
        filename_dxf: str,
        body_placement: str = "max_breadth",
        body_sides: str = None,
    ):
        body_lines = self.body_lines(body_placement, body_sides)
        grid_options = {}
        if body_placement == "right":
            # run the base line and the waterlines through the body plan,
            # draw the body plan centerline
            grid_options = self.body_plan_grid_options(body_lines, body_sides)

        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf, **grid_options)

            dxf.add_red_polyline(self.loft_line_n(0))
            dxf.add_red_polyline(self.loft_line_n(1))
            dxf.add_red_polyline(self.loft_line_n(2))
            dxf.add_red_polyline(self.loft_line_n(3))
            dxf.add_red_polyline(self.loft_line_n(4))
            #
            dxf.add_red_polyline(self.loft_line_n(6))
            dxf.add_red_polyline(self.loft_line_n(7))
            dxf.add_red_polyline(self.loft_line_n(8))
            dxf.add_red_polyline(self.loft_line_n(9))
            dxf.add_red_polyline(self.loft_line_n(10))
            dxf.add_red_polyline(self.loft_line_n(11))
            dxf.add_red_polyline(self.loft_line_n(12))

            # the ghost line: plan view, profile view (the body lines have it
            # as points)
            dxf.add_red_polyline(self.loft_ghost_plan_line())
            dxf.add_red_polyline(self.loft_ghost_profile_line())

            # the diagonals in the plan view, below the plan centerline
            self.plot_diagonal_plan_lines(dxf)

            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = Project89()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project89.dxf"))
    print("Saved as:", out("tutorial_project89.dxf"))
    # option 2: the body plan to the right of the profile view, clear of it
    proj.save_model_as(out("tutorial_project89_body_right.dxf"), body_placement="right")
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        out("tutorial_project89_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as(out("tutorial_project89_body.dxf"))
    print("Saved as:", out("tutorial_project89_body.dxf"))
    # the body line of single stations, every point labelled
    for station in ("14", "16", "18"):
        filename = out("tutorial_project89_station%s.dxf" % station)
        proj.save_station_as(filename, station)
        print("Saved as:", filename)

# end of file
