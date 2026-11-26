"""Blue Moon: model for sample_data_too/offset_table_blue_moon.csv.

The table has 9 stations (1-8 and TRAN.) in two halves: heights (upper rows,
e.g. "LWL to SHEER", "BASE TO B-2") and half-breadths (lower rows, e.g.
"SHEER", "LWL"). Heights named "BASE ..." are measured from the base line;
"LWL to ..." heights are measured from the LWL, which is ``_y_lwl`` above the
base. The grid (stations, waterlines, buttocks, rabbet, keel, sheet) is read
from sample_data_too/offset_table_blue_moon.meta.

Run: ``python3 projectbluemoon.py [--out-dir DIR] [--output-units UNIT]`` writes, into ./out (in the
current directory) or DIR, tutorial_project_blue_moon.dxf (everything, body lines in
the middle of the profile view), tutorial_project_blue_moon_body_right.dxf (body
plan to the right of the profile view), tutorial_project_blue_moon_body_split.dxf
(aft/forward halves) and tutorial_project_blue_moon_body.dxf (body lines only).
"""

import context
from context import table_of_offsets

import os


#
# Model implementation specific for the sample data
#
class ProjectBlueMoon(table_of_offsets.Model):
    def __init__(self):
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data_too/offset_table_blue_moon.csv",
            ),
            unit="ftin",
        )
        self._y_lwl = 4 * 12 + 1 + 7.0 / 8.0  # 4-1-7

    def base_offset(self, line_name: str):
        """(virtual) Returns the vertical offset for the given line"""
        if line_name in ["LWL to SHEER", "LWL to DECK EDG"]:
            return self._y_lwl

        # the line_name is one of 'plane' lines
        if line_name in [
            "SHEER",
            "WL 2A",
            "WL 1A",
            "LWL",
            "WL 1B",
            "WL 2B",
            "RABBET",
            "KEEL",
            "BALLAST TOP",
        ]:
            return self.plan_centerline_y()

        return 0

    # 0         LWL to SHEER
    # 1      LWL to DECK EDG
    # 2          BASE TO B-3
    # 3          BASE TO B-2
    # 4          BASE TO B-1
    # 5       RABBET TO BASE
    # 6         KEEL TO BASE
    # 7     CENTERLINE SHAFT
    # 8     BASE TO TOP BAL.

    # 9                SHEER
    # 10               WL 2A
    # 11               WL 1A
    # 12                 LWL
    # 13               WL 1B
    # 14               WL 2B
    # 15              RABBET
    # 16                KEEL
    # 17         BALLAST TOP
    # 18            D. UPPER
    # 19            D. LOWER

    # {'LWL to SHEER': 0, 'LWL to DECK EDG': 1, 'BASE TO B-3': 2, 'BASE TO B-2': 3, 'BASE TO B-1': 4, 'RABBET TO BASE': 5, 'KEEL TO BASE': 6, 'CENTERLINE SHAFT': 7, 'BASE TO TOP BAL.': 8, 'SHEER': 9, 'WL 2A': 10, 'WL 1A': 11, 'LWL': 12, 'WL 1B': 13, 'WL 2B': 14, 'RABBET': 15, 'KEEL': 16, 'BALLAST TOP': 17, 'D. UPPER': 18, 'D. LOWER': 19, nan: 20, 'RED-CORRECTED': 21}

    def diagonal_extension(self):
        """The diagonals reach 6" beyond the farthest hull point"""
        return 6.0

    def keel_body_point(self):
        return ("KEEL", "KEEL TO BASE")

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: polyline} with the body plan line of every station"""
        # (breadth, height) pairs. A string is a table row, a number is inches.
        body_points = [
            ("SHEER", "LWL to SHEER"),
            ("RABBET", "RABBET TO BASE"),
            ("KEEL", "KEEL TO BASE"),
            ("BALLAST TOP", "BASE TO TOP BAL."),
            # the waterlines are added by loft_body_lines (waterlines_positions)
            # buttocks: height from the table, breadth is the buttock
            (36.0, "BASE TO B-3"),
            (24.0, "BASE TO B-2"),
            (12.0, "BASE TO B-1"),
        ]
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
            # rows 5 and 6 (RABBET TO BASE, KEEL TO BASE) are drawn by
            # plot_keel_and_rabbet below, with the extra points
            dxf.add_red_polyline(self.loft_line_n(7))
            dxf.add_red_polyline(self.loft_line_n(8))
            #
            # now half-breadth
            #
            dxf.add_red_polyline(self.loft_line_n(9))
            dxf.add_red_polyline(self.loft_line_n(10))
            dxf.add_red_polyline(self.loft_line_n(11))
            dxf.add_red_polyline(self.loft_line_n(12))
            dxf.add_red_polyline(self.loft_line_n(13))
            dxf.add_red_polyline(self.loft_line_n(14))

            # the keel and the rabbet, in the profile and plan views, as the
            # grid file gives them ([keel], [rabbet]), with the extra points
            self.plot_keel_and_rabbet(dxf)

            # draw a body line

            # the pairs of point making a body line
            """
            #,1,2,3,4,5,6,7,8,TRAN.
------------------ Y -----------------------------
LWL to SHEER,3-6-5,3-0-0,2-6-4,2-2-5,2-0-3,1-11-7,2-1-7,2-3-1,2-7-4
LWL to DECK EDG,2-6-5,2-0-1,1-6-5,1-2-6,1-0-4,1-0-0,1-2-0,1-5-2,1-8-2
BASE TO B-3,,,4-10-1,3-5-7,3-3-6,3-8-1,4-7-0,5-4-6,
BASE TO B-2,,5-5-7,3-6-0,2-11-0,2-10-5,3-2-7,4-1-2,4-9-2,5-0-2
BASE TO B-1,,3-9-3,2-8-3,2-3-7,2-4-4,2-9-0,3-8-6,4-5-5,4-7-2
RABBET TO BASE,4-7-4,2-11-0,2-0-5,1-7-3,1-3-1,1-1-7,3-2-1,4-3-0,4-3-4
KEEL TO BASE,4-1-7,2-4-6,1-4-2,0-9-3,0-5-2,0-2-1,1-7-3,4-1-7,
CENTERLINE SHAFT,,,,,,3-0-4,2-9-6,,
BASE TO TOP BAL.,,,1-8-3,1-5-4,1-2-6,0-8-3,,,
--------------------- X --------------------------
SHEER,0-10-0,2-8-0,3-9-0,4-2-4,4-4-0,4-1-4,3-6-2,3-1-1,2-6-2
WL 2A,0-5-0,2-0-7,3-4-7,4-1-7,4-4-2,4-1-7,3-6-6,3-1-6,2-10-1
WL 1A,0-2-7,1-8-3,3-0-6,3-11-6,4-4-0,4-0-7,3-4-2,2-3-1,1-9-0
LWL,,1-3-0,2-7-0,3-6-5,4-0-6,3-8-6,2-1-3,0-1-0,0-1-0
WL 1B,,0-7-7,1-10-6,2-10-3,3-1-6,2-4-1,0-4-7,,
WL 2B,,,0-11-4,1-6-4,1-6-4,0-10-1,0-2-4,,
RABBET,0-2-0,0-2-2,0-2-6,0-3-0,0-3-0,0-3-0,0-3-0,0-3-0,0-3-0
KEEL,0-0-4,0-0-4,0-1-4,0-3-0,0-3-0,0-3-0,0-1-0,0-1-0,0-1-0
BALLAST TOP,,,0-2-0,0-3-0,0-3-0,0-3-0,,,
D. UPPER,0-7-0,2-1-7,3-3-7,4-1-5,4-4-7,4-1-2,3-2-4,2-5-6,
D. LOWER,,1-0-0,1-9-3,2-1-5,2-1-6,2-2-4,0-10-7,,
,,,,,,,,,
RED-CORRECTED,,,,,,,,,
            """

            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = ProjectBlueMoon()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project_blue_moon.dxf"))
    print("Saved as:", out("tutorial_project_blue_moon.dxf"))
    # option 2: the body plan to the right of the profile view, clear of it
    proj.save_model_as(
        out("tutorial_project_blue_moon_body_right.dxf"), body_placement="right"
    )
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        out("tutorial_project_blue_moon_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as(out("tutorial_project_blue_moon_body.dxf"))
    print("Saved as:", out("tutorial_project_blue_moon_body.dxf"))

# end of file
