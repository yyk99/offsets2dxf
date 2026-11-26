"""Little Maid of Kent: model of
sample_data_too/little_maid_of_kent/offset_table_little_maid_of_kent.csv

Offset table No. 675, 30'-0" x 24'-0" x 10'-0" x 5'-0", a V bottom aux'l
schooner. The table is from a picture (a private submodule; run ``git
submodule update --init``), in feet-inches-eighths; the model works in inches
(``ftin`` is a format). The grid (the stations placed right to left, the bow
``A`` on the right; the waterlines; the chine, rabbet and keel rows; the sheet
layout) is in the meta data file offset_table_little_maid_of_kent.meta next to
the CSV, which is still being filled in.

A hard chine hull: the table gives the sheer, the chine and the rabbet, and
the half-breadths of the waterlines ``LL 6`` .. ``LL 2``.

Table layout: stations ``A``, ``0`` .. ``12``, ``C``, ``S``; ``Height Sheer``
(measured up from the LWL, see ``base_offset``), ``Height
Chine``, ``Height B1``, ``Height Rabbet``, ``Height Top of Iron Keel``,
``Height Keel``, ``Height Prop Shaft`` (heights above the base line),
``Breadth Sheer``, ``Breadth LL 6`` .. ``Breadth LL 2``, ``Breadth Chine``
(half-breadths) and ``Diagonal D1``, ``D2``, ``D4`` (in the grid file; drawn
in the plan view). The cells of ``Height Keel``
and ``Height Top of Iron Keel`` that are ``straight`` are filled with the values
on the straight line.

Run: ``python3 project_little_maid.py [--out-dir DIR] [--output-units UNIT]``
writes, into ./out (in the current directory) or DIR,
tutorial_project_little_maid.dxf (everything, the body lines in the middle of
the profile view), tutorial_project_little_maid_body_split.dxf (everything, the
split body plan to the right of the profile view) and
tutorial_project_little_maid_body.dxf (the body view alone).
"""

import context
from context import table_of_offsets

import os


class ProjectLittleMaid(table_of_offsets.Model):
    def __init__(self):
        # the grid is read from the .meta file next to the CSV
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data_too/little_maid_of_kent/"
                "offset_table_little_maid_of_kent.csv",
            )
        )

    def base_offset(self, line_name: str):
        """The sheer height is measured from the LWL, the other heights from
        the base line: ``Height Sheer`` is shifted up by the height of the
        LWL. The half-breadths are drawn above the centerline of the plan
        view."""
        if line_name == "Height Sheer":
            return self.waterlines_positions()["LWL"]
        if line_name.startswith("Breadth "):
            return self.plan_centerline_y()
        return 0.0

    def waterline_row(self, name: str):
        """The half-breadth row of the waterline ``LL 4`` is ``Breadth LL 4``"""
        return "Breadth " + name

    def body_points(self):
        """The (breadth, height) points of a body line, without the
        waterlines (``loft_body_lines`` adds them): the sheer, the chine and
        the rabbet and the buttock B1. The stations where a cell is empty have no such point.
        """
        return [
            ("Breadth Sheer", "Height Sheer"),
            self.chine_body_point(),
            self.rabbet_body_point(),
            # the buttock B1: its height from the table, its half-breadth
            # from [buttocks] of the meta data file
            (self.buttocks_positions()["B1"], "Height B1"),
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
        self, filename_dxf: str, placement: str = "max_breadth", sides: str = None
    ):
        """Save the body lines and their grid alone."""
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
            # draw the body plan centerline, the buttocks and the diagonals
            grid_options = self.body_plan_grid_options(body_lines, body_sides)
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf, **grid_options)

            # profile view
            for name in ["Height Sheer", "Height Chine", "Height B1"]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # plan view
            for name in [
                "Breadth Sheer",
                "Breadth LL 6",
                "Breadth LL 4",
                "Breadth LL 3",
                "Breadth LL 2",
                "Breadth Chine",
            ]:
                dxf.add_red_polyline(self.loft_line_n_sorted(self.line_to_index(name)))

            # the keel and the rabbet, in the profile and plan views, as the
            # meta data file gives them ([keel], [rabbet])
            self.plot_keel_and_rabbet(dxf)

            # the diagonals in the plan view, below the plan centerline
            self.plot_diagonal_plan_lines(dxf)

            # body plan
            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = ProjectLittleMaid()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project_little_maid.dxf"))
    print("Saved as:", out("tutorial_project_little_maid.dxf"))
    # the body plan to the right of the profile view, clear of it: the aft
    # stations left of its centerline, the forward stations right
    proj.save_model_as(
        out("tutorial_project_little_maid_body_split.dxf"),
        body_placement="right",
        body_sides="split",
    )
    print("Saved as:", out("tutorial_project_little_maid_body_split.dxf"))
    proj.save_body_lines_as(out("tutorial_project_little_maid_body.dxf"))
    print("Saved as:", out("tutorial_project_little_maid_body.dxf"))

# end of file
