#
#
#

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
            )
        )
        # fmt: off
        self.set_under_waterline(
            {
            }
        )
        # fmt: on
        self._y_lwl = 4 * 12 + 1 + 7.0 / 8.0  # 4-1-7
        self._y0 = 0.0
        self._y1 = -120.0
        pass

    def station_positions(self):
        """Return a dictionary of station positions
        waterlines 0-9-0
        stations   3-0-0
        butts      1-0-0
        7..8       1-8-4
        """
        station_positions = {}
        for c in self._too.columns:
            if c == "#":
                pass
            elif c == "TRAN.":
                station_positions[c] = 0.0
            elif c == "8":
                station_positions[c] = 3 * 12 - 20.5  #  1-8-4 == 20.5
            else:
                assert c.isdecimal()
                station_positions[c] = (8 - int(c)) * 12 * 3  # 1' == 12" (inches)
        return station_positions

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
            return self._y1

        return 0

    def grid_y_origins(self):
        """(virtual) we want two horizontal (central) grid lines"""
        return [0, -10 * 12.0]

    def waterlines_positions(self):
        wl = {
            "WL 2A": 18.0,
            "WL 1A": 9.0,
            "LWL": 0.0,
            "WL 1B": -9.0,
            "WL 2B": -18.0,
        }
        for k in wl:
            wl[k] += self._y_lwl
        return wl

    def buttocks_positions(self):
        return {"BASE TO B-3": 36.0, "BASE TO B-2": 24.0, "BASE TO B-1": 12.0}

    def grid_y_origins(self):
        """(virtual): central lines will be drawn here"""
        return [self._y0, self._y1]

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

    def breadth_line_to_index(self: object, line_id: str) -> int:
        """virtual: "sheer" -> 0"""
        line_ids = list(self._too["#"])
        line_id_to_index = {line_ids[idx]: idx for idx in range(9, 20)}
        print(line_id_to_index)  # DEBUG
        return line_id_to_index

    def height_line_to_index(self: object, line_id: str) -> int:
        """virtual: "rabbet" -> 0"""
        return {
            "LWL to SHEER": 0,
            "LWL to DECK EDG": 1,
            "BASE TO B-3": 2,
            "BASE TO B-2": 3,
            "BASE TO B-1": 4,
            "RABBET TO BASE": 5,
            "KEEL TO BASE": 6,
            "CENTERLINE SHAFT": 7,
            "BASE TO TOP BAL.": 8,
        }

    def save_model_as(self, filename_dxf: str):
        with table_of_offsets.DXF(filename_dxf) as dxf:
            self.plot_grid(dxf)

            dxf.add_red_polyline(self.loft_line_n(0))
            dxf.add_red_polyline(self.loft_line_n(1))
            dxf.add_red_polyline(self.loft_line_n(2))
            dxf.add_red_polyline(self.loft_line_n(3))
            dxf.add_red_polyline(self.loft_line_n(4))
            dxf.add_red_polyline(self.loft_line_n(5))
            dxf.add_red_polyline(self.loft_line_n(6))
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

            body_points = [
                ("sheer", "sheer line"),
                "WL 1",
                "WL 2",
                ("rabbet", "rabbet line"),
            ]
            dxf.add_red_polyline(self.loft_body_line("5", body_points))


if __name__ == "__main__":
    proj = ProjectBlueMoon()
    proj.save_model_as("test_project_blue_moon.dxf")
    print("Saved as:", os.path.abspath("test_project_blue_moon.dxf"))

# end of file
