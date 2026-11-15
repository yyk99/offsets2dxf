# Tabby Cat

A small boat; the lines plan ("Teoreticheskiy chertezh") with its table of
offsets ("Tablitsa plazovykh ordinat, mm") is in the picture.

Files:

- `offset_table.csv` - the table of offsets as in the picture, in
  millimetres. Stations `1`..`12`; rows `Height ...` (above the baseline:
  Sheer, Buttock 1-4, Rabbet, Keel), `Breadth ...` (half-breadths from the
  centerline: Sheer, WL I-VIII, Rabbet) and `Diagonal D1`, `D2`. A dash in the
  source is an empty cell. Row names are English; the source names are
  Bort (LB) = Sheer, Batoks B1-B4 = Buttock 1-4, Shpunt (Shp.) = Rabbet, Kil
  (LK) = Keel, Vaterliniya VLI-VLVIII = WL I-VIII (VLV is the design waterline,
  KVL), D1, D2 = diagonals.
- `teoreticheskiy_chertezh_tebbi_ket.jpg` - the lines plan (profile, plan)
  and the table.
- `konstruktivnyy_midel-shpangout_2.jpg` - the construction midship section
  (not used).

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
see the assumptions in its docstring. The diagonals are not used.
