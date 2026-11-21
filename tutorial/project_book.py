"""The book table: model of sample_data_too/book/offset_table.csv

Source: "Lofting a Boat" by Roger Kopanycia, see sample_data_too/book/
(a private submodule; run ``git submodule update --init``). The table is in
millimetres (``unit="mm"``); the model works in inches. The grid (stations,
waterlines, buttocks, sheet layout) is in the meta data file
sample_data_too/book/offset_table.grid, lengths in millimetres.

Table layout: stations ``FP``, ``1A``, ``1`` .. ``5``, ``TR``; ``Height
Sheer``, ``Breadth Sheer`` (half-breadth), ``Breadth WL 1`` .. ``WL 7``
(half-breadths), ``Height B1`` and ``Height B2`` (heights of the buttocks
B1 and B2), ``Height R/L`` (the rabbet line, as read by the user; no
half-breadth in the table: it is half of the constant rabbet siding of the
grid file). The diagonals ``Diagonal D1``, ``Diagonal D2`` (their lines are not
known) are not used.

Run: ``python3 project_book.py [--out-dir DIR] [--output-units UNIT]``
writes, into ./out (in the current directory) or DIR,
tutorial_project_book.dxf (everything), tutorial_project_book_body_split.dxf
(the split body view alone) and tutorial_project_book_rl.dxf (the profile view of the rabbet line R/L).
"""

import context
from context import table_of_offsets

import os


class ProjectBook(table_of_offsets.Model):
    def __init__(self):
        # the grid is read from offset_table.grid next to the CSV
        super().__init__(
            os.path.join(
                os.path.dirname(__file__),
                "../sample_data_too/book/offset_table.csv",
            )
        )

    def base_offset(self, line_name: str):
        """The half-breadths are drawn above the centerline of the plan view."""
        if line_name.startswith("Breadth "):
            return self.grid_y_origins()[1]
        return 0

    def rabbet_body_point(self):
        """``R/L`` is the rabbet line (the user's reading). The table has no
        half-breadth for it: it is half of the rabbet siding (``[siding]
        rabbet`` of the grid file, the same along the rabbet), 0 if the file
        has none."""
        return (self.siding("rabbet", 0.0) / 2, "Height R/L")

    def body_points(self):
        """The (breadth, height) points of a body line, without the waterlines
        (``loft_body_lines`` adds them)."""
        return [("Breadth Sheer", "Height Sheer"), self.rabbet_body_point()] + [
            (offset, "Height " + name)
            for name, offset in self.buttocks_positions().items()
        ]

    def body_lines(
        self, placement: str = "max_breadth", sides: str = None, bow_station=None
    ):
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

    def save_buttock_profile_as(self, filename_dxf: str, buttock: str = "B1"):
        """Save the profile view of one line (the row ``Height <name>``: a
        buttock, ``R/L``) with the grid."""
        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf)
            row = self.line_to_index("Height " + buttock)
            dxf.add_red_polyline(self.loft_line_n(row))

    def save_model_as(self, filename_dxf: str, body_placement: str = "max_breadth"):
        body_lines = self.body_lines(body_placement)
        grid_options = {}
        if body_placement == "right":
            grid_options = self.body_plan_grid_options(body_lines)

        with self.open_dxf(filename_dxf) as dxf:
            self.plot_grid(dxf, **grid_options)

            # profile view
            for name in ["Height R/L", "Height B1", "Height B2", "Height Sheer"]:
                dxf.add_red_polyline(self.loft_line_n(self.line_to_index(name)))

            # plan view; a waterline is not drawn across the stations where
            # the sheer is below it (the empty cells of the table)
            for name in ["Breadth WL %d" % n for n in range(1, 8)] + [
                "Breadth Sheer"
            ]:
                for line in self.loft_line_n_runs(self.line_to_index(name)):
                    dxf.add_red_polyline(line)

            # the rabbet line in the plan view: a constant half-breadth (half
            # of the siding) at the stations where the table has its height
            y_plan = self.grid_y_origins()[1] + self.rabbet_body_point()[0]
            rabbet = self.loft_line_n(self.line_to_index("Height R/L"))
            dxf.add_red_polyline([(x, y_plan) for x, _ in rabbet])

            # the keel: a straight line in the profile view, a constant
            # half-breadth (half of the siding) in the plan view
            (x0, y0), (x1, y1) = self.keel_line()
            dxf.add_red_polyline([(x0, y0), (x1, y1)])
            y_keel = self.grid_y_origins()[1] + self.siding("keel", 0.0) / 2
            dxf.add_red_polyline([(x0, y_keel), (x1, y_keel)])

            # body plan
            self.plot_body_lines(dxf, body_lines)


if __name__ == "__main__":
    args = table_of_offsets.parse_script_args(description=__doc__)
    out_dir = args.out_dir

    def out(name):
        return os.path.join(out_dir, name)

    proj = ProjectBook()
    proj.set_output_unit(args.output_units)
    proj.save_model_as(out("tutorial_project_book.dxf"))
    print("Saved as:", out("tutorial_project_book.dxf"))
    proj.save_body_lines_as(out("tutorial_project_book_body_split.dxf"))
    print("Saved as:", out("tutorial_project_book_body_split.dxf"))
    # the profile view of the rabbet line alone
    proj.save_buttock_profile_as(out("tutorial_project_book_rl.dxf"), "R/L")
    print("Saved as:", out("tutorial_project_book_rl.dxf"))

# end of file
