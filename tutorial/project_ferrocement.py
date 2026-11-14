"""A ferrocement hull: model of sample_data/a_ferrocement_hull/offset_table.csv

Source: https://www.fao.org/4/v9468e/v9468e05.htm (see the images next to the
table). The table is in millimetres (``unit="mm"``); the model works in inches.

Table layout: stations ``T`` (transom) and ``1`` .. ``12``; rows named
``Height ...`` are heights above the baseline (Buttock I-III, Keel, Knuckle,
Deck, Sheer, Diagonal A-C), rows named ``Breadth ...`` are half-breadths from
the centerline (Keel, WL 1-8, Knuckle, Deck, Sheer). The cells marked "-" in
the source are empty.

Assumptions (not in the table):

- the stations are 1000 mm apart; the transom ``T`` is at x = 0 (it is the
  station 0 of the drawing) and the bow is at station 12;
- the buttocks are 500 mm apart (Buttock I, II, III at 500, 1000, 1500 mm);
- the heights of the waterlines are not in the table, so the waterlines are
  neither drawn nor used for the body lines, and the diagonals are not drawn.

Run: ``python3 project_ferrocement.py`` (from tutorial/) writes
test_project_ferrocement.dxf (everything), test_project_ferrocement_body_right.dxf
(body plan to the right of the profile view),
test_project_ferrocement_body_split.dxf (aft/forward halves) and
test_project_ferrocement_body.dxf (body lines only).
"""

import context
from context import table_of_offsets

import os

MM = 1.0 / 25.4  # inches in a millimetre


class ProjectFerrocement(table_of_offsets.Model):
    def __init__(self):
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data/a_ferrocement_hull/offset_table.csv",
            ),
            unit="mm",
        )
        self.set_bow_station("12")
        # the plan view is drawn below the profile view
        self._y_plan = -80.0

    def station_positions(self):
        """The transom T is at x = 0, the stations 1..12 are 1 m apart."""
        return {c: (0 if c == "T" else int(c)) * 1000 * MM for c in self._stations()}

    def _stations(self):
        return [c for c in self._too.columns if c != "#"]

    def base_offset(self, line_name: str):
        """The half-breadths are drawn above the centerline of the plan view."""
        if line_name.startswith("Breadth "):
            return self._y_plan
        return 0

    def buttocks_positions(self):
        return {"B I": 500 * MM, "B II": 1000 * MM, "B III": 1500 * MM}

    def waterlines_positions(self):
        """The heights of the waterlines are not in the table."""
        return {}

    def grid_y_origins(self):
        """the baseline of the profile view, the centerline of the plan view"""
        return [0.0, self._y_plan]

    def drawing_area_vertical_borders(self):
        return (self._y_plan - 20, 130.0)

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: [polyline, ...]}: the body plan lines.

        Points are (half-breadth, height above the baseline) in inches: the
        sheer, the deck, the knuckle, the keel and the three buttocks.
        """
        # (breadth, height): a string is a table row, a number is inches
        body_points = [
            ("Breadth Sheer", "Height Sheer"),
            ("Breadth Deck", "Height Deck"),
            ("Breadth Knuckle", "Height Knuckle"),
            ("Breadth Keel", "Height Keel"),
        ]
        body_points += [
            (offset, "Height Buttock " + name[2:])
            for name, offset in self.buttocks_positions().items()
        ]
        return self.loft_body_lines(
            body_points, placement, sides=sides, bow_station=bow_station
        )

    def save_body_lines_as(
        self, filename_dxf: str, placement: str = "max_breadth", sides: str = None
    ):
        """Save the body lines only (no grid, no plan/profile lines)"""
        with table_of_offsets.DXF(filename_dxf) as dxf:
            for poly in self.body_polylines(self.body_lines(placement, sides)):
                dxf.add_red_polyline(poly)

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

        with table_of_offsets.DXF(filename_dxf) as dxf:
            self.plot_grid(dxf, **grid_options)

            # profile view
            for name in [
                "Height Buttock I",
                "Height Buttock II",
                "Height Buttock III",
                "Height Keel",
                "Height Knuckle",
                "Height Deck",
                "Height Sheer",
            ]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # plan view
            for name in [
                "Breadth Keel",
                "Breadth WL 1",
                "Breadth WL 2",
                "Breadth WL 3",
                "Breadth WL 4",
                "Breadth WL 5",
                "Breadth WL 6",
                "Breadth WL 7",
                "Breadth WL 8",
                "Breadth Knuckle",
                "Breadth Deck",
                "Breadth Sheer",
            ]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # body plan
            for poly in self.body_polylines(body_lines):
                dxf.add_red_polyline(poly)


if __name__ == "__main__":
    proj = ProjectFerrocement()
    proj.save_model_as("test_project_ferrocement.dxf")
    print("Saved as:", os.path.abspath("test_project_ferrocement.dxf"))
    # the body plan to the right of the profile view, clear of it
    proj.save_model_as("test_project_ferrocement_body_right.dxf", body_placement="right")
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        "test_project_ferrocement_body_split.dxf",
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as("test_project_ferrocement_body.dxf")

# end of file
