# Tabby Cat

A small boat; the lines plan ("Teoreticheskiy chertezh") with its table of
offsets ("Tablitsa plazovykh ordinat, mm") is in the picture.

Files:

- `offset_table.csv` - the table of offsets as in the picture, in
  millimetres. Stations `1`..`12`; rows `Height ...` (above the baseline:
  Sheer, Buttock 1-4, Rabbet, Keel), `Breadth ...` (half-breadths from the
  centerline: Sheer, WL I-VIII, Rabbet, Keel) and `Diagonal D1`, `D2`. A dash in the
  source is an empty cell, except `Breadth Rabbet` at the stations 5-8, which
  is 85 mm like at the stations 4 and 9, and `Height Keel` at the stations 6-9,
  which is a straight line from station 5 (345) to station 10 (200): 316, 287,
  258, 229 (the source has dashes there).
  `Breadth Keel` is not in the source: it was added, equal to
  `Breadth Rabbet`, as the breadth the designer assumed for the keel. Row names are English; the source names are
  Bort (LB) = Sheer, Batoks B1-B4 = Buttock 1-4, Shpunt (Shp.) = Rabbet, Kil
  (LK) = Keel, Vaterliniya VLI-VLVIII = WL I-VIII (VLV is the design waterline,
  KVL), D1, D2 = diagonals.
- `teoreticheskiy_chertezh_tebbi_ket.jpg` - the lines plan (profile, plan)
  and the table.
- `konstruktivnyy_midel-shpangout_2.jpg` - the construction midship section;
  its body plan shows the lines of the diagonals D1 and D2 with dimensions.

Known about the hull (not in the table):

- the waterlines above the baseline: WL I 600, WL II 700, WL III 800,
  WL IV 900, WL V (KVL) 1000, WL VI 1150, WL VII 1300, WL VIII 1450 mm;
- the stations are 510 mm apart (confirmed; the drawing: 510, 510, 305 near
  the stem);
  the bow is station 1;
- the buttocks 1-4 are 300 mm apart (300, 600, 900, 1200 mm from the
  centerline); at station 6 the buttock heights fit the sections through the
  waterline points with this spacing.

`tutorial/project_tabby_cat.py` reads the table with
`Model(csv, unit="mm")` and draws the profile, the plan and the body lines;
see the assumptions in its docstring. The diagonals D1 and D2 are drawn in the
construction midsection (`konstruktivnyy_midel-shpangout_2.jpg`): both lines
start on the centerline 1700 mm above the baseline; D1 ends on the baseline
1100 mm from the centerline, D2 ends 1850 mm from the centerline on the design
waterline (1000 mm). The table gives the distance along them from the start to
the hull.
