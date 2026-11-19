Sample data directory

Tables of offsets (CSV) used by the scripts in ../tutorial. More tables are in
the sample_data_too git submodule.

offset_table.csv
    The primary sample (project 89). Offsets in feet-inches-eighths
    (e.g. 1-10-2), 33 stations. Used by tutorial/project89.py.

a_ferrocement_hull/
    A ferrocement hull from an FAO publication, see its README.md.
    offset_table.csv         the table of offsets as in the source, in
                             millimetres (plain numbers; a dash in the
                             source is an empty cell); stations T and 1..12;
                             rows "Height ..." (above the baseline) and
                             "Breadth ..." (half-breadths)
    ferrocement_offsets.gif  the source table and the drawing it is taken from
    ferrocement_lines.gif    the lines plan (buttocks 500 mm apart, diagonals)
    ferrocement_transom_details.gif  the transom
    Used by tutorial/project_ferrocement.py, which reads the table with
    Model(csv, unit="mm"). The table is kept in its own unit; the program
    converts the values to inches (see "unit" in ../README.md).

tabby_cat/
    A small boat: the lines plan and the table of offsets (picture), see its
    README.md.
    offset_table.csv         the table as in the picture, in millimetres;
                             stations 1..12; rows "Height ...", "Breadth ..."
                             and "Diagonal ..."
    Used by tutorial/project_tabby_cat.py (Model(csv, unit="mm")).

CSV format
    First column "#": the line names. The other columns: stations. A cell is
    an offset in the unit of the table (feet-inches-eighths by default); an
    empty cell means "no point". See ../README.md.
