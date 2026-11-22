"""The 28' Cutter Njord: model of sample_data_too/28ft_cutter/offset_table.csv

The table is from a picture (a private submodule; run ``git submodule update
--init``), in feet-inches-eighths; the model works in inches. The grid (the
stations placed right to left, the bow on the right; the rabbet rows; the
sheet layout) is in the meta data file offset_table.grid next to the CSV.

A hard chine hull: the table gives the sheer, the chine and the rabbet, but
no waterlines and no buttocks (the grid file has empty ``[waterlines]`` and
``[buttocks]`` sections), so the sections are straight between those points.

Table layout: stations ``0``, ``C-1``, ``2`` .. ``26`` (even), ``27``,
``28``; ``Height Sheer``, ``Height Chine``, ``Height Rabbet`` (heights above
the base line; ``Height Keel`` is empty), ``Breadth Sheer``, ``Breadth
Chine``, ``Breadth Rabbet`` (half-widths). The cells of ``Breadth Rabbet``
between the stations ``C-1`` and ``27`` are ``straight`` (the "STRAIGHT LINE"
of the picture): the model fills them with the values on the straight line.
The sheer is empty at ``C-1`` and ``27``, the chine and the rabbet are empty
at ``0`` and ``28``.

Run: ``python3 project_28ft_cutter.py [--out-dir DIR] [--output-units UNIT]``
writes, into ./out (in the current directory) or DIR,
tutorial_project_28ft_cutter.dxf (everything, the body lines in the middle of
the profile view) and tutorial_project_28ft_cutter_body_split.dxf (the split
body view alone: the stern stations on the left of the centerline, the bow
stations on the right).
"""

import context
from context import table_of_offsets

import os


class Project28ftCutter(table_of_offsets.Model):
    def __init__(self):
        # the grid is read from offset_table.grid next to the CSV
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data_too/28ft_cutter/offset_table.csv",
            )
        )

    def base_offset(self, line_name: str):
        """The half-widths are drawn above the centerline of the plan view."""
        if line_name.startswith("Breadth "):
            return self.plan_centerline_y()
        return 0.0

    def body_points(self):
        """The (breadth, height) points of a body line: the sheer, the chine
        and the rabbet (from the grid file). The stations where a cell is
        empty have no such point."""
        return [
            ("Breadth Sheer", "Height Sheer"),
            ("Breadth Chine", "Height Chine"),
            self.rabbet_body_point(),
        ]

    def body_lines(
        self,
        placement: str = "max_breadth",
        sides: str = None,
        bow_station: str = None,
    ):
        """Return {station: [polyline, ...]}: the body plan lines. Points are
        (half-breadth, height above the base line) in inches."""
        return self.loft_body_lines(
            self.body_points(), placement, sides=sides, bow_station=bow_station
        )

    def save_body_lines_as(
        self, filename_dxf: str, placement: str = "max_breadth", sides: str = "split"
    ):
        """Save the body view alone; ``sides="split"``: the stern stations on
        the left of the centerline, the bow stations on the right."""
        with self.open_dxf(filename_dxf) as dxf:
            lines = self.body_lines(placement, sides)
            self.plot_body_plan_grid(dxf, lines)
            self.plot_body_lines(dxf, lines)

    def save_model_as(self, filename_dxf: str):
        body_lines = self.body_lines()
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf)

            # profile view
            for name in ["Height Sheer", "Height Chine"]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # plan view
            for name in ["Breadth Sheer", "Breadth Chine"]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # the rabbet, in the profile and plan views, as the grid file
            # gives it ([rabbet])
            self.plot_keel_and_rabbet(dxf)

            # body plan
            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = Project28ftCutter()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project_28ft_cutter.dxf"))
    print("Saved as:", out("tutorial_project_28ft_cutter.dxf"))
    proj.save_body_lines_as(out("tutorial_project_28ft_cutter_body_split.dxf"))
    print("Saved as:", out("tutorial_project_28ft_cutter_body_split.dxf"))

# end of file
