# A ferrocement hull

See: https://www.fao.org/4/v9468e/v9468e05.htm

Files:

- `offset_table.csv` - the table of offsets as in `ferrocement_offsets.gif`,
  in millimetres. Stations `T` and `1`..`12`; rows `Height ...` (above the
  baseline) and `Breadth ...` (half-breadths from the centerline).
- `ferrocement_offsets.gif` - the table and the drawing it belongs to.
- `ferrocement_lines.gif` - the lines plan (stations 0..20, buttocks B1-B3,
  diagonals A-C).
- `ferrocement_transom_details.gif` - the transom.

Known about the hull (not in the table):

- draught 1800 mm: the design waterline (DWL) is the waterline 5 of the table
  and is 1800 mm above the baseline;
- the waterlines are 250 mm apart (WL 1 is 800 mm, WL 8 is 2550 mm above the
  baseline);
- the buttocks are spaced 500 mm (Buttock I, II, III at 500, 1000, 1500 mm);
- characteristics at the DWL, from the lines plan: length overall 12.80 m,
  length of waterline 12.00 m, breadth max. 4.28 m, depth 1.99 m,
  displacement volume 24.72 m3 (25.34 tonnes), prismatic coefficient 0.588.

Caveat: the breadth and the depth above do not match the offsets table (the
deck half-breadth is at most 1562 mm, the sheer is up to 2985 mm above the
baseline), so the lines plan and the table may show different hulls.

`tutorial/project_ferrocement.py` uses the draught and the waterline
distance for the waterlines; see the assumptions in its docstring.
