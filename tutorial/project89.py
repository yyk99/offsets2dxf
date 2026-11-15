"""Project 89: model of the sample table (sample_data/offset_table.csv).

Heights (Sheer, B 3', B 2', B 1', Rabbet, Profile) are measured from the LWL,
positive up. Half-breadths are the "1/2w Deck", "WL ..." and "... Plan" rows.
Some cells hold two values ("0-2-0 and 0-3-0"); such points are skipped in the
body lines.

The bow is station 0 (``set_bow_station``); the stern, station 33, is at x = 0.

Body plan sides (``body_sides``): ``"half"``, ``"both"`` (both halves) or
``"split"`` (aft stations on the left, forward on the right). The default is
``"split"`` for the body plan in the middle of the profile view and ``"half"``
for the others.

Body plan placement (``body_placement``): ``"max_breadth"`` (default) puts the
body lines in the middle of the profile view, ``"right"`` puts them to the
right of it.

Run: ``python3 project89.py [--out-dir DIR] [--output-units UNIT]`` writes, into ./out (in the
current directory) or DIR, test_project89.dxf (everything),
test_project89_body_right.dxf (body plan to the right),
test_project89_body_split.dxf (aft/forward halves) and
test_project89_body.dxf (body lines only).
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
        self.set_bow_station("0")  # the stem; the stern (station 33) is at x = 0
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

    def buttocks_positions(self):
        return {"B 3'": 3 * 12.0, "B 2'": 2 * 12.0, "B 1'": 12 * 1.0}

    def waterlines_positions(self):
        return {
            "WL + 2'": 2 * 12.0,
            "WL + 1'": 12.0,
            'WL + 6"': 6.0,
            "LWL": 0.0,
            'WL - 6"': -6.0,
            "WL - 1'": -12.0,
            "WL - 2'": -24.0,
            "WL - 3'": -36.0,
            "WL - 4'": -4 * 12,
        }

    def drawing_area_vertical_borders(self):
        """(virtual)"""
        return (-12 * 10, 20 * 12)

    def grid_y_origins(self):
        """(virtual) we want two horizontal grid lines"""
        return [0, 10 * 12.0]

    def keel_body_point(self):
        return ("Profile Plan", "Profile")

    def rabbet_body_point(self):
        return ("Rabbet Plan", "Rabbet")

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: polyline} with the body plan line of every station.

        Points are (half-breadth, height above the LWL) in inches.
        """
        # (breadth, height): a string is a table row, a number is inches
        body_points = [
            ("1/2w Deck", "Sheer"),
            ("Rabbet Plan", "Rabbet"),
            ("Profile Plan", "Profile"),
        ]
        # the waterlines are added by loft_body_lines (waterlines_positions)
        # buttocks: height from the table, breadth is the buttock
        body_points += [(36.0, "B 3'"), (24.0, "B 2'"), (12.0, "B 1'")]
        return self.loft_body_lines(
            body_points, placement, sides=sides, bow_station=bow_station
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

            self.plot_body_lines(dxf, body_lines)

if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = Project89()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("test_project89.dxf"))
    print("Saved as:", out("test_project89.dxf"))
    # option 2: the body plan to the right of the profile view, clear of it
    proj.save_model_as(out("test_project89_body_right.dxf"), body_placement="right")
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        out("test_project89_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as(out("test_project89_body.dxf"))
    print("Saved as:", out("test_project89_body.dxf"))

# end of file
