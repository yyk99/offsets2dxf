# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Converts a boat's lines plan "table of offsets" (CSV, values in feet-inches-eighths such as `1-10-2`) into DXF drawings using `ezdxf`. Units are inches. Core library is the single module `table_of_offsets.py`; per-project scripts live in `tutorial/`.

## Commands

    python3 -m venv ~/.venvs/off2dxf && source ~/.venvs/off2dxf/bin/activate
    pip3 install -r requirements.txt        # numpy, pandas, ezdxf, black

    python -m unittest discover -v -s ./tests -p "test_*.py"     # all tests (same args as .vscode/settings.json)
    python -m unittest discover -s ./tests -p "test_*.py" -k offset2double   # single test by name

    black .                                  # formatter (format-on-save in VS Code)

Tutorial scripts (e.g. `tutorial/project89.py`) are run directly and write `.dxf` files; the checked-in `test_*.dxf` files in the repo root are such outputs.

## Architecture

- `TableOfOffsets.offset2double` parses `F-I-E` strings to inches. Trailing `+`/`-` means +/- 1/16". Missing parts are allowed (`1-0`, `3`).
- `Model` wraps a pandas DataFrame read from the CSV. First column `#` is the line name (Sheer, `B 3'`, ...); other columns are station numbers. Station x-position is `(33 - station) * 12` (hard-coded for the 33-station sample layout). It is a base class: subclasses override the "(virtual)" methods (`waterlines_positions`, `buttocks_positions`, `base_offset`, `grid_y_origins`, `drawing_area_vertical_borders`, `breadth_line_to_index`, `height_line_to_index`). `set_under_waterline` marks stations where a line's offsets are negated (see `offset_sign`).
- `DXF` is a context manager around an `ezdxf` R2010 doc with layers `grid`, `red`, `text`. It saves on exit. Note that `__exit__` re-raises as a bare `Exception` and returns True.
- `tutorial/projectNN.py` / `projectbluemoon.py` each subclass `Model` for one boat's CSV, then plot the grid and lofted lines. `tutorial/context.py` and `tests/context.py` put the repo root on `sys.path` so `import table_of_offsets` works; scripts and tests import via `from context import ...`.

## Body plan

`loft_body_line(station, [(breadth, height), ...])` builds one body line; each item is a table row name or a number in inches. `breadth_at` / `height_at` look rows up by name (`breadth_line_to_index` / `height_line_to_index` are overridable). `breadth_at` ignores `base_offset` (sheet placement is vertical only). `ProjectBlueMoon.body_lines()` is the reference example; Options: `placement` (`"max_breadth"` default = centerline on the widest station, `"right"` = clear of the profile view, `"raw"`) and `sides` (`"half"`, `"both"`, `"split"` = aft stations left, forward right; the bow end comes from `set_bow_station(station)` / the `bow_station` argument, default the greater x). Both projects now produce body lines. With `placement="right"`, `body_plan_grid_options()` gives `plot_grid` the extension of the base line (first `grid_y_origins`) and waterlines plus a vertical body plan centerline and the buttock lines (`buttocks_positions`). `loft_body_lines` returns `{station: [polyline, ...]}`; `body_polylines()` flattens it.

## Data

`sample_data/` holds the primary CSV. `sample_data_too/` is a git submodule (`git@github.com:yyk99/tables_of_offsets.git`) with more tables (`offset_table_181.csv`, `offset_table_blue_moon.csv`). Run `git submodule update --init` to fetch it.
