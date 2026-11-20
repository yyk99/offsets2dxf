## Create a DXF file from a boat table of offsets

## REQUIRED packagas

    See requirements.txt

## BUILD and TESTING

### Linux

    git clone .../offsets2dxf
    cd offsets2dxf
    python3 -m venv ~/.venvs/off2dxf
    source ~/.venvs/off2dxf/bin/activate
    pip3 install -r requirements.txt

### Windows

In Visual Studio Code

    - Command Palette (Ctrl+Shift+P) 
        -> environment -> venv -> select python -> [x] requirements


## REFERENCES

    1. https://docs.python-guide.org/writing/structure/#test-suite

## USAGE

The coordinates in the `.dxf` files are in the unit of the table of offsets
(inches for the feet-inches-eighths tables, millimetres for the ferrocement
hull); `--output-units inch|ft|mm|cm|m` (or `Model.set_output_unit`) chooses
another one. The unit is also stored in the file. The program itself works in
inches.

Run a project script; it writes its `.dxf` files into `./out` in the current
directory (git-ignored, created if needed). Use `--out-dir DIR` to write
somewhere else (a relative `DIR` is relative to the current directory):

    cd tutorial
    python3 projectbluemoon.py      # -> tutorial/out/tutorial_project_blue_moon*.dxf
    python3 project89.py --out-dir /tmp/dxf

Run the tests:

    python3 -m unittest discover -v -s ./tests -p "test_*.py"

More tables of offsets are in the `sample_data_too` git submodule
(`git submodule update --init`).

## TABLE OF OFFSETS FORMAT

A CSV file. The first column (header `#`) holds line names (`Sheer`, `B 3'`,
`LWL` ...), the other columns are stations. Cells hold offsets as
`feet-inches-eighths`; an empty cell means "no point":

    #,33,32,30
    Sheer,,1-10-2,1-8-6
    B 3',,,1-8-6

- `1-10-2` = 1 ft 10 in 2/8 in = 22.25 in; `0-1` = 1 in; `1` = 12 in
- a trailing `+` / `-` adds / subtracts 1/16 in: `0-0-1+` = 0.1875 in
- all lengths inside the program are inches
- a table in another unit (plain numbers, e.g. millimetres, empty cell for a
  dash) is read with the `unit` option: `Model(csv, unit="mm")`. Units:
  `"ftin"` (default, feet-inches-eighths), `"inch"`, `"ft"`, `"mm"`, `"cm"`,
  `"m"`. The table is kept as it is in the source; the values are converted
  to inches when they are read. See
  `tutorial/project_ferrocement.py` (`sample_data/a_ferrocement_hull/`).

## ADDING A NEW BOAT

1. Put the CSV into `sample_data_too/` (or anywhere).
2. Copy a script from `tutorial/` and subclass `table_of_offsets.Model`.
   Override what differs from the defaults (see the `Model` docstring):
   `station_positions`, `waterlines_positions`, `buttocks_positions`,
   `base_offset`, `grid_y_origins`, `drawing_area_vertical_borders`,
   `set_under_waterline`.
3. Loft lines with `loft_line_n(row)` (plan/profile lines) or
   `loft_body_line(station, [(breadth, height), ...])` (body plan lines);
   draw them with the `DXF` context manager.
   `projectbluemoon.py` is the most complete example.

## BODY PLAN OPTIONS

`Model.loft_body_lines(body_points, placement, sides)` (see
`tutorial/projectbluemoon.py` and `tutorial/project89.py`):

- `placement="max_breadth"` (default) - the body plan centerline is on the
  station with the greatest breadth, in the middle of the profile view;
  `"right"` - to the right of the profile view, clear of it;
  `"raw"` - no shift.
- `sides` - `"half"`: the half-breadth only; `"both"`: both halves of
  every station; `"split"`: the usual body plan, aft stations to the left and
  forward stations to the right of the centerline. The bow end is given by
  `Model.set_bow_station("<station>")` (or the `bow_station` argument); if it
  is not set, the bow is the end with the greater x. The tutorial projects set
  it in `__init__`.
  The default is `"split"` for a body plan in the middle of the profile view
  (`placement="max_breadth"`) and `"half"` otherwise (`Model.body_plan_sides`);
  pass `sides` to choose another one.

With `placement="right"` the base line and the waterlines of the profile view
are extended through the body plan, and its vertical centerline and its buttock
lines (`buttocks_positions`, to the right of the centerline for
`sides="half"`, on both sides otherwise) are drawn
(`Model.body_plan_grid_options`, `Model.plot_grid`).

The waterlines are always part of the body lines when the table has them:
`loft_body_lines` adds a point for every waterline of `waterlines_positions()`
whose half-breadth row is in the table (the row name is the waterline name;
override `Model.waterline_row(name)` if it differs, e.g. "WL 1" ->
"Breadth WL 1"). The height is the position of the waterline.

The diagonals of a body plan are given by the overridable
`Model.diagonals_positions()`: `{name: (y0, x1, y1)}` in inches, heights above
the base line. A diagonal is the straight line from the point `(0, y0)` on the
centerline through the point `(x1, y1)`; the table cell of a station is the
distance along that line from `(0, y0)` to the hull (the row name is the
diagonal name, or `Model.diagonal_row(name)`). Like the waterlines, the hull
points of the diagonals that have a row in the table are added to every body
line (`Model.diagonal_body_points`, `DiagonalPoint`), and the diagonals are
drawn as grid lines, named at the second point (`Model.diagonal_segments`).
In the plan view the half-breadths of the diagonal points are drawn below the
centre line, opposite to the waterlines (`Model.loft_diagonal_plan_lines`,
`Model.plot_diagonal_plan_lines`).
The default is no diagonals.

The first of the `body_points` is the sheer. `loft_body_lines` joins the
sheer points of the consecutive stations into the sheer line, one polyline per
side of the centerline. A station whose table cell for the sheer is empty is
skipped (the line is not extrapolated). `loft_body_lines` returns a
`BodyLines`, a `dict` `{station: [polyline, ...]}` with the attribute `sheer`
(`Model.body_sheer_polylines(lines)`).

The rabbet line and the keel line are made the same way from the points
returned by the overridable `Model.rabbet_body_point()` and
`Model.keel_body_point()` (a `(breadth, height)` item as in `body_points`;
`None`, the default, means no such line); `BodyLines.rabbet`, `BodyLines.keel`,
`Model.body_rabbet_polylines(lines)`, `Model.body_keel_polylines(lines)`. The
keel line (the keel points of the stations) is not the keel link below.

The lowest point of every body line (the keel) is joined to the centerline by
a horizontal segment; pass `keel_link=False` to omit it.

`Model.plot_body_lines(dxf, lines)` draws the body lines and writes the
station name above the top end of every body line (`labels=False` to omit)
and the sheer, rabbet and keel lines (`sheer=False`, `rabbet=False`,
`keel=False` to omit).
`Model.plot_body_plan_grid(dxf, lines)` draws the grid of a body plan alone:
the base line, the waterlines, the centerline `CL`, the buttock lines and the
diagonals.

Each tutorial script writes the full drawing, a variant with the body plan to
the right, a split one and a body-lines-only file (with the grid, the sheer,
rabbet and keel lines and the keel links).

## DOCUMENTATION OF THE CODE

Module, class and method docstrings in `table_of_offsets.py`.
