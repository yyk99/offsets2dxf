"""Tabby Cat with the grid from a meta data file.

The same model as project_tabby_cat.py (see there for the source and the
table layout), but everything the grid file can say is read from
sample_data/tabby_cat/offset_table.meta: the stations (510 mm apart, the
stern at x = 0, the bow is station 1), the waterlines, the buttocks, the
diagonals D1 and D2, the rabbet rows and the sheet layout. What is left in
this file: the rows of the keel (a body point per station), the rows of the
buttock heights and what to draw.

The output is the same as that of project_tabby_cat.py, with the names
tutorial_project_tabby_cat_meta*.dxf.

Run: ``python3 project_tabby_cat_meta.py [--out-dir DIR] [--output-units UNIT]``
writes, into ./out (in the current directory) or DIR,
tutorial_project_tabby_cat_meta.dxf (everything),
tutorial_project_tabby_cat_meta_body_right.dxf (body plan to the right of the
profile view), tutorial_project_tabby_cat_meta_body_split.dxf (aft/forward
halves), tutorial_project_tabby_cat_meta_body.dxf (body lines only) and
tutorial_project_tabby_cat_meta_station6.dxf (the body line of the station 6
with the table rows the coordinates of every point come from).
"""

import context
from context import table_of_offsets

import os


class ProjectTabbyCatMeta(table_of_offsets.Model):
    def __init__(self):
        # the grid is read from offset_table.meta next to the CSV
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data/tabby_cat/offset_table.csv",
            )
        )

    def base_offset(self, line_name: str):
        """The half-breadths are drawn above the centerline of the plan view."""
        if line_name.startswith("Breadth "):
            return self.plan_centerline_y()
        return 0

    def keel_body_point(self):
        return ("Breadth Keel", "Height Keel")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        (``loft_body_lines`` adds them): a string is a table row, a number is
        inches. The rabbet is from the grid file; it is listed so that the
        annotated station has it too (``loft_body_lines`` does not add it
        twice)."""
        body_points = [
            ("Breadth Sheer", "Height Sheer"),
            self.rabbet_body_point(),
            ("Breadth Keel", "Height Keel"),
        ]
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

        Points are (half-breadth, height above the baseline) in the unit of the table: the
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
                "Height Sheer",
            ]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # plan view
            for name in [
                "Breadth Keel",
                "Breadth WL I",
                "Breadth WL II",
                "Breadth WL III",
                "Breadth WL IV",
                "Breadth WL V",
                "Breadth WL VI",
                "Breadth WL VII",
                "Breadth WL VIII",
                "Breadth Sheer",
            ]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # the rabbet, in the profile and plan views, as the grid file
            # gives it ([rabbet])
            self.plot_keel_and_rabbet(dxf)

            # the diagonals in the plan view, below its centerline
            self.plot_diagonal_plan_lines(dxf)

            # body plan
            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = ProjectTabbyCatMeta()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project_tabby_cat_meta.dxf"))
    print("Saved as:", out("tutorial_project_tabby_cat_meta.dxf"))
    # the body plan to the right of the profile view, clear of it
    proj.save_model_as(
        out("tutorial_project_tabby_cat_meta_body_right.dxf"),
        body_placement="right",
    )
    # the usual body plan: aft stations left, forward stations right
    proj.save_model_as(
        out("tutorial_project_tabby_cat_meta_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    proj.save_body_lines_as(out("tutorial_project_tabby_cat_meta_body.dxf"))
    # one station, every point labelled with the source of its coordinates
    proj.save_station_as(out("tutorial_project_tabby_cat_meta_station6.dxf"), "6")
    print("Saved as:", out("tutorial_project_tabby_cat_meta_body.dxf"))

# end of file
