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

Run a project script from the `tutorial/` directory; it writes a `.dxf` file
into the current directory:

    cd tutorial
    python3 projectbluemoon.py      # -> test_project_blue_moon.dxf (+ _body.dxf)
    python3 project89.py

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

## DOCUMENTATION OF THE CODE

Module, class and method docstrings in `table_of_offsets.py`.
