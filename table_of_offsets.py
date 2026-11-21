"""Create a DXF drawing from a boat's table of offsets.

A table of offsets is a CSV file:

- the first column (header ``#``) holds the line names, one per row
  (e.g. ``Sheer``, ``B 3'``, ``LWL``);
- the other columns are stations (e.g. ``33``, ``32`` ... ``0``, or ``TRAN.``);
- a cell holds an offset, by default in feet-inches-eighths, e.g. ``1-10-2``
  (see ``TableOfOffsets.offset2double``), or a plain number in the unit given
  to ``Model`` (``unit="mm"``, see ``TableOfOffsets.UNITS``); an empty cell
  means "no point".

All lengths inside this module are in inches (see ``Model.units``), whatever
the unit of the table.

Classes:

- ``TableOfOffsets`` - parsing of the offset strings.
- ``Model`` - base class: loads a CSV and lofts polylines (plan, profile and
  body plan lines). Subclass it for each boat, see ``tutorial/``.
- ``DXF`` - thin context-manager wrapper around ``ezdxf`` that saves the file.
"""

import argparse
import copy
import math
import os
import re
import tomllib

import ezdxf
import ezdxf.entities
import ezdxf.units
import ezdxf.enums
import numpy
import pandas
import math

__version__ = "0.5.0"

# the .dxf files written by the scripts go here by default: ./out in the
# current directory (git-ignored)
DEFAULT_OUT_DIR = "out"


def parse_script_args(argv: list = None, description: str = None):
    """Parse the command line of a script:
    ``[--out-dir DIR] [--output-units UNIT]``.

    Returns the namespace with:

    - ``out_dir`` - the absolute path of the directory for the output files:
      ``out`` in the current directory if not given (``DEFAULT_OUT_DIR``); a
      relative ``DIR`` is also relative to the current directory. The
      directory is created when a file is saved (see ``DXF.close``);
    - ``output_units`` - the unit of the coordinates in the .dxf files
      (``inch``, ``ft``, ``mm``, ``cm`` or ``m``), None if not given: the unit
      of the table is used (see ``Model.set_output_unit``).
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help="directory for the .dxf files (default: %(default)s)",
    )
    parser.add_argument(
        "--output-units",
        choices=OUTPUT_UNITS,
        default=None,
        help="unit of the coordinates in the .dxf files "
        "(default: the unit of the table of offsets)",
    )
    args = parser.parse_args(argv)
    args.out_dir = os.path.abspath(args.out_dir)
    return args


def output_dir_from_args(argv: list = None, description: str = None) -> str:
    """The ``out_dir`` of ``parse_script_args``."""
    return parse_script_args(argv, description).out_dir


class TableOfOffsets:
    """Helpers to convert offsets written as ``feet-inches-eighths`` to inches."""

    def __init__(self):
        pass

    @staticmethod
    def verify_triplet(w: list):
        """Validate the parts of an offset split by "-". Not implemented yet:
        always returns True."""
        return True

    @staticmethod
    def offset2double(triplet: str):
        """Convert an offset string to inches (float).

        Format: ``feet-inches-eighths``; trailing parts may be omitted:
        ``1-10-2`` -> 12 + 10 + 2/8 = 22.25, ``0-1`` -> 1.0, ``1`` -> 12.0.
        A trailing ``+`` or ``-`` means plus/minus 1/16 inch:
        ``0-0-1+`` -> 0.1875, ``0-0-1-`` -> 0.0625.
        Raises an exception for a malformed string.
        """
        delta = 0
        if triplet[-1] == "-":
            delta = -1.0 / 16
            triplet = triplet[:-1]
        elif triplet[-1] == "+":
            delta = 1.0 / 16.0
            triplet = triplet[:-1]

        w = triplet.split("-")
        TableOfOffsets.verify_triplet(w)
        d = 0
        if len(w) == 3:
            d = int(w[0]) * 12.0 + int(w[1]) + int(w[2]) / 8.0
        elif len(w) == 2:
            d = int(w[0]) * 12.0 + int(w[1])
        elif len(w) == 1:
            d = int(w[0]) * 12.0
        else:
            raise ValueError("bad offset format: %r" % (triplet,))
        return d + delta


# Units of the offsets in a table: the number of inches in one unit.
# "ftin" is the special feet-inches-eighths notation, see offset2double.
TableOfOffsets.UNITS = {
    "ftin": None,
    "inch": 1.0,
    "ft": 12.0,
    "mm": 1.0 / 25.4,
    "cm": 1.0 / 2.54,
    "m": 1000.0 / 25.4,
}


# Units of the coordinates in a .dxf file: the unit of the table, except "ftin".
OUTPUT_UNITS = ("inch", "ft", "mm", "cm", "m")


# What to do with a cell that holds several values ("0-2-0 and 0-3-0"):
# "error" (default) - the cell is malformed (ValueError), "first" - use the
# first value.
MULTI_VALUE_POLICIES = ("error", "first")

# the separator of the values in such a cell
MULTI_VALUE_SEPARATOR = re.compile(r"\s+and\s+")


def offset_to_inches(
    value: str, unit: str = "ftin", multi_value: str = "error"
) -> float:
    """Convert an offset from a table cell to inches.

    multi_value - what to do with a cell of the form ``offset1 and offset2``,
    one of ``MULTI_VALUE_POLICIES``: ``"error"`` (default) raises ValueError,
    ``"first"`` uses ``offset1``.

    unit - one of ``TableOfOffsets.UNITS``: ``"ftin"`` (default) is the
    ``feet-inches-eighths`` notation, the others are plain numbers, e.g.
    ``offset_to_inches("1290", "mm")`` -> 50.79...
    Raises ValueError for an unknown unit or a malformed value.
    """
    if unit not in TableOfOffsets.UNITS:
        raise ValueError(
            "unknown unit %r, expected one of %s" % (unit, list(TableOfOffsets.UNITS))
        )
    if multi_value not in MULTI_VALUE_POLICIES:
        raise ValueError(
            "unknown multi_value policy %r, expected one of %s"
            % (multi_value, list(MULTI_VALUE_POLICIES))
        )
    if multi_value == "first":
        value = MULTI_VALUE_SEPARATOR.split(value.strip())[0]
    if unit == "ftin":
        return TableOfOffsets.offset2double(value)
    return float(value) * TableOfOffsets.UNITS[unit]


# the extensions of a meta data file ("meta" and "grid" are synonyms)
META_EXTENSIONS = (".meta", ".grid")

# the sections of a meta data file and the keys of the plain ones
_META_KEYS = {
    "table": {"csv", "unit", "bow_station", "multi_value"},
    "stations": {"origin", "spacing", "positions"},
    "ghost_line": {"row", "height"},
    "keel": {"from", "to", "siding"},
    "rabbet": {"siding", "height_row", "breadth_row"},
    "sheet": {"y_origins", "vertical_borders"},
}
# the sections with one entry per name
_META_NAMED = {"waterlines", "buttocks", "diagonals"}
_META_ENTRY_KEYS = {
    "waterlines": {"height", "row"},
    "diagonals": {"row", "from", "through"},
}


def find_meta(csv_path: str):
    """The meta data file of a table: the CSV path with the extension replaced
    by one of ``META_EXTENSIONS`` (``.meta`` or ``.grid``), or ``None`` if
    there is none. Raises ValueError if both exist."""
    stem = os.path.splitext(csv_path)[0]
    found = [stem + e for e in META_EXTENSIONS if os.path.exists(stem + e)]
    if len(found) > 1:
        raise ValueError("more than one meta data file: %s" % ", ".join(found))
    return found[0] if found else None


def _meta_lengths_to_inches(meta: dict, k: float) -> dict:
    """A copy of ``meta`` with every length multiplied by ``k`` (inches in a
    unit of the table; 1 for ``ftin`` and ``inch``)."""
    if k == 1.0:
        return meta
    meta = copy.deepcopy(meta)
    st = meta.get("stations", {})
    for key in ("origin", "spacing"):
        if key in st:
            st[key] *= k
    for name in st.get("positions", {}):
        st["positions"][name] *= k
    for name in meta.get("buttocks", {}):
        meta["buttocks"][name] *= k
    for section in ("keel", "rabbet"):
        if "siding" in meta.get(section, {}):
            meta[section]["siding"] *= k
    for d in meta.get("waterlines", {}).values():
        d["height"] *= k
    for d in meta.get("diagonals", {}).values():
        d["from"] = [v * k for v in d["from"]]
        d["through"] = [v * k for v in d["through"]]
    for end in ("from", "to"):
        if end in meta.get("keel", {}):
            meta["keel"][end]["height"] *= k
    if "height" in meta.get("ghost_line", {}):
        meta["ghost_line"]["height"] *= k
    sheet = meta.get("sheet", {})
    for key in ("y_origins", "vertical_borders"):
        if key in sheet:
            sheet[key] = [v * k for v in sheet[key]]
    return meta


def load_meta(path: str) -> dict:
    """Read and check a meta data file (TOML, see
    ``sample_data/offset_table.meta``) that describes the grid of a model:
    ``[table]``, ``[stations]``, ``[waterlines]``, ``[buttocks]``,
    ``[diagonals]``, ``[keel]``, ``[rabbet]``, ``[ghost_line]`` and ``[sheet]``. Lengths are in the unit of the
    table (``[table] unit``; inches for ``ftin``), the model converts them
    to inches.
    Raises ValueError for an unknown section or key or a malformed value."""
    with open(path, "rb") as f:
        try:
            meta = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError("%s: %s" % (path, e))

    def bad(what):
        return ValueError("%s: %s" % (path, what))

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    for section, content in meta.items():
        if section not in _META_KEYS and section not in _META_NAMED:
            raise bad("unknown section [%s]" % section)
        if not isinstance(content, dict):
            raise bad("[%s] must be a table" % section)
        if section in _META_KEYS:
            unknown = set(content) - _META_KEYS[section]
            if unknown:
                raise bad("unknown key %r in [%s]" % (sorted(unknown)[0], section))
    unit = meta.get("table", {}).get("unit", "ftin")
    if unit not in TableOfOffsets.UNITS:
        raise bad("unknown unit %r" % (unit,))
    policy = meta.get("table", {}).get("multi_value", "error")
    if policy not in MULTI_VALUE_POLICIES:
        raise bad("unknown multi_value policy %r" % (policy,))
    stations = meta.get("stations", {})
    if "stations" in meta:
        for key in ("origin", "spacing"):
            if key in stations and not number(stations[key]):
                raise bad("[stations] %s must be a number" % key)
        positions = stations.get("positions")
        if positions is not None and not (
            isinstance(positions, dict) and all(map(number, positions.values()))
        ):
            raise bad("[stations] positions must be {station = x, ...} (numbers)")
        if "spacing" not in stations and not positions:
            raise bad("[stations] needs spacing or positions")
    for name, value in meta.get("buttocks", {}).items():
        if not number(value):
            raise bad("buttock %r must be a number" % name)
    for end in ("from", "to"):
        if end in meta.get("keel", {}):
            e = meta["keel"][end]
            if (
                not isinstance(e, dict)
                or set(e) != {"station", "height"}
                or not isinstance(e["station"], str)
                or not number(e["height"])
            ):
                raise bad("[keel] %s must be { station = \"..\", height = N }" % end)
    for section in ("keel", "rabbet"):
        value = meta.get(section, {}).get("siding")
        if "siding" in meta.get(section, {}) and (not number(value) or value <= 0):
            raise bad("[%s] siding must be a positive number" % section)
    rabbet = meta.get("rabbet", {})
    for key in ("height_row", "breadth_row"):
        if key in rabbet and not (isinstance(rabbet[key], str) and rabbet[key]):
            raise bad("[rabbet] %s must be the name of a table row" % key)
    if "breadth_row" in rabbet and "height_row" not in rabbet:
        raise bad("[rabbet] breadth_row needs height_row")
    for section in ("waterlines", "diagonals"):
        for name, entry in meta.get(section, {}).items():
            if not isinstance(entry, dict):
                raise bad("%s %r must be a table" % (section, name))
            unknown = set(entry) - _META_ENTRY_KEYS[section]
            if unknown:
                raise bad("unknown key %r in %s %r" % (sorted(unknown)[0], section, name))
    for name, entry in meta.get("waterlines", {}).items():
        if not number(entry.get("height")):
            raise bad("waterline %r needs a number height" % name)
    for name, entry in meta.get("diagonals", {}).items():
        for key in ("from", "through"):
            point = entry.get(key)
            if not (
                isinstance(point, list) and len(point) == 2 and all(map(number, point))
            ):
                raise bad("diagonal %r: %s must be [x, y]" % (name, key))
        if entry["from"][0] != 0:
            raise bad("diagonal %r: from must be on the centerline [0, y0]" % name)
    ghost = meta.get("ghost_line")
    if ghost is not None and not (
        isinstance(ghost.get("row"), str) and number(ghost.get("height"))
    ):
        raise bad("[ghost_line] needs a row and a number height")
    sheet = meta.get("sheet", {})
    for key in ("y_origins", "vertical_borders"):
        if key in sheet and not (
            isinstance(sheet[key], list) and all(map(number, sheet[key]))
        ):
            raise bad("[sheet] %s must be a list of numbers" % key)
    if "vertical_borders" in sheet and len(sheet["vertical_borders"]) != 2:
        raise bad("[sheet] vertical_borders must be [bottom, top]")
    return meta


class DiagonalPoint:
    """A point of a body line given by a diagonal: the table cell is the
    distance along the diagonal from its first point ``(0, y0)`` on the
    centerline toward its second point ``(x1, y1)``. Heights are above the base
    line, all in inches. It can be used as an item of ``body_points`` (see
    ``Model.diagonals_positions``).

    ``row`` is the name of the table row with the distances.
    """

    def __init__(self, row: str, y0: float, x1: float, y1: float):
        length = math.hypot(x1, y1 - y0)
        if length == 0:
            raise ValueError("the two points of the diagonal %r coincide" % (row,))
        self.row = row
        self.y0, self.x1, self.y1 = y0, x1, y1
        self._ux, self._uy = x1 / length, (y1 - y0) / length

    def point(self, distance: float):
        """``(breadth, height)`` of the point ``distance`` from ``(0, y0)``."""
        return (distance * self._ux, self.y0 + distance * self._uy)


class GhostPoint:
    """A point of a body line on the "ghost line": the half-breadth is the
    second value of a table cell ``offset1 and offset2`` of the row ``row``,
    the height is ``height`` (inches above the base line). A station whose cell
    has no second value has no such point. It can be used as an item of
    ``body_points`` (see ``Model.ghost_line``)."""

    def __init__(self, row: str, height: float):
        self.row = row
        self.height = height


class BodyLines(dict):
    """The result of ``Model.loft_body_lines``: ``{station: [polyline, ...]}``
    with the attributes ``sheer``, ``rabbet`` and ``keel``, the sheer line, the
    rabbet line and the keel line (see ``Model.body_sheer_polylines``,
    ``Model.body_rabbet_polylines`` and ``Model.body_keel_polylines``)."""

    sheer = ()
    rabbet = ()
    keel = ()


class Model:
    """A boat's table of offsets (loaded from CSV) and the geometry lofted from it.

    This is a base class. Subclass it for each boat and override the hooks
    that differ from the defaults:

    - ``station_positions`` - x position of every station column;
    - ``waterlines_positions``, ``buttocks_positions`` - reference lines to
      draw on the grid;
    - ``base_offset`` - vertical shift of a line on the drawing sheet;
    - ``grid_y_origins``, ``drawing_area_vertical_borders`` - grid layout;
    - ``breadth_line_to_index``, ``height_line_to_index`` - map a line name to
      a table row (default: look the name up in the ``#`` column);
    - ``set_under_waterline`` - mark offsets that must be negated.

    Typical use (see ``tutorial/projectbluemoon.py``)::

        class MyBoat(Model):
            ...

        with DXF("out.dxf") as dxf:
            boat.plot_grid(dxf)
            dxf.add_red_polyline(boat.loft_line_n(0))
    """

    def __init__(self: object, _filename_csv: str, unit: str = None, meta=None):
        """Load the table of offsets from ``_filename_csv``.

        unit - the unit of the offsets in the table, one of
        ``TableOfOffsets.UNITS``: ``"ftin"`` (feet-inches-eighths),
        ``"inch"``, ``"ft"``, ``"mm"``, ``"cm"`` or ``"m"``. Everything the
        model returns is in inches. The default is the unit of the meta data
        file, else ``"ftin"``.

        meta - the meta data file that describes the grid (see ``load_meta``):
        a path, ``None`` (default) for the file next to the CSV with the
        extension ``.meta`` or ``.grid`` if there is one (``find_meta``), or
        ``False`` for none. What it
        gives (stations, waterlines, buttocks, diagonals, ghost line, sheet
        layout, bow station, multi value policy) is the default of the
        "(virtual)" methods, which a subclass still can override.
        """
        if meta is None:
            meta = find_meta(_filename_csv) or False
        self._meta = load_meta(meta) if meta else {}
        meta_table = self._meta.get("table", {})
        if unit is None:
            unit = meta_table.get("unit", "ftin")
        elif "unit" in meta_table and unit != meta_table["unit"]:
            raise ValueError(
                "unit %r does not agree with the meta data file (%r)"
                % (unit, meta_table["unit"])
            )
        if unit not in TableOfOffsets.UNITS:
            raise ValueError(
                "unknown unit %r, expected one of %s"
                % (unit, list(TableOfOffsets.UNITS))
            )
        self._unit = unit
        self._meta = _meta_lengths_to_inches(
            self._meta, TableOfOffsets.UNITS[unit] or 1.0
        )
        self._multi_value = meta_table.get("multi_value", "error")
        self._filename_csv = _filename_csv
        # read the cells as text: the numbers are converted by offset_to_inches
        self._too = pandas.read_csv(self._filename_csv, dtype=str)
        self._under_waterline = {}
        # x of the centerline of the body plan lofted last (loft_body_lines)
        self.body_plan_centerline_x = None
        self._bow_station = None
        if "bow_station" in meta_table:
            self.set_bow_station(meta_table["bow_station"])
        self._output_unit = None

    def set_bow_station(self, station: str):
        """Tell which station is at the bow end, e.g. ``"1"`` or ``"0"``.

        It decides which stations are "forward" for ``sides="split"`` in
        ``loft_body_lines``. If it is not set, the bow is assumed to be at the
        greater x of ``station_positions``.
        """
        if station is not None and station not in self.station_positions():
            raise KeyError("unknown station: %r" % (station,))
        self._bow_station = station

    def bow_station(self):
        """The station set by ``set_bow_station`` (None if not set)."""
        return self._bow_station

    def set_under_waterline(self, d: dict):
        """Set the offsets to be negated, as ``{line_name: [station, ...]}``.
        Used where a table gives positive values below the waterline."""
        self._under_waterline = d

    def units(self):
        """Name of the length unit used for all returned values."""
        return "inch"

    def offsets_unit(self):
        """The unit of the offsets in the CSV table (the ``unit`` argument)."""
        return self._unit

    def offset_to_inches(self, value: str) -> float:
        """Convert a cell of the table to inches, using the unit of the table."""
        return offset_to_inches(value, self._unit, self._multi_value)

    def set_multi_value_policy(self, policy: str):
        """What to do with a cell that holds several values, ``offset1 and
        offset2``: one of ``MULTI_VALUE_POLICIES``; ``"error"`` (default) makes
        the point malformed (it is skipped where the cells are optional),
        ``"first"`` uses ``offset1``."""
        if policy not in MULTI_VALUE_POLICIES:
            raise ValueError(
                "unknown multi_value policy %r, expected one of %s"
                % (policy, list(MULTI_VALUE_POLICIES))
            )
        self._multi_value = policy

    def set_output_unit(self, unit: str = None):
        """Set the unit of the coordinates in the .dxf files (``OUTPUT_UNITS``).
        None (the default) means the unit of the table (``"inch"`` for the
        feet-inches-eighths tables)."""
        if unit is not None and unit not in OUTPUT_UNITS:
            raise ValueError(
                "unknown output unit %r, expected one of %s" % (unit, OUTPUT_UNITS)
            )
        self._output_unit = unit

    def output_unit(self) -> str:
        """The unit of the coordinates in the .dxf files: the one set by
        ``set_output_unit``, else the unit of the table."""
        if self._output_unit is not None:
            return self._output_unit
        return "inch" if self._unit == "ftin" else self._unit

    def open_dxf(self, filename_dxf: str):
        """A ``DXF`` to write ``filename_dxf`` in the output unit. The model
        itself works in inches; the coordinates are converted when drawn."""
        return DXF(filename_dxf, unit=self.output_unit())

    def station_positions(self):
        """(virtual) Return ``{station_name: x_position}`` for every station column.

        Station names are just labels (``"1"``, ``"T"``, ``"AP"``, ``"1A"``);
        the position of a station is derived from its place in the list of
        the columns of the table: the n-th station (from 0) is at
        ``origin + n * spacing`` inches. ``origin`` (default 0) and
        ``spacing`` (default 12; may be negative, to number the stations from
        the bow, whose x is the greater) are those of ``[stations]`` of the
        meta data file. ``positions`` of ``[stations]`` gives the x of
        stations by name, for tables whose stations are not equally spaced; the
        others use ``origin`` and ``spacing``. Override this method for other
        layouts. Raises ValueError for a station that has no position.
        """
        stations = self._meta.get("stations", {})
        explicit = stations.get("positions", {})
        names = [c for c in self._too.columns if c != "#"]
        unknown = [n for n in explicit if n not in names]
        if unknown:
            raise ValueError(
                "[stations] positions: %r is not a station of the table" % unknown[0]
            )
        origin = stations.get("origin", 0)
        spacing = stations.get("spacing", None if explicit else 12)
        station_positions = {}
        for n, c in enumerate(names):
            if c in explicit:
                station_positions[c] = float(explicit[c])
            elif spacing is not None:
                station_positions[c] = origin + n * spacing
            else:
                raise ValueError("no position for station %r" % (c,))
        return station_positions

    def buttocks_positions(self):
        """(virtual) Return a dictionary
        E.g.
        {
            "LWL" : 0,
        }
        From ``[buttocks]`` of the meta data file, if any.
        """
        if "buttocks" in self._meta:
            return {k: float(v) for k, v in self._meta["buttocks"].items()}
        print("TODO: please define buttocks_positions()")
        return {}

    def siding(self, name: str, default: float = None) -> float:
        """The siding of the element ``name`` (``"keel"`` or ``"rabbet"``), in
        inches: its breadth, the full width across the centerline. From the
        key ``siding`` of the section ``[keel]`` or ``[rabbet]`` of the meta
        data file; ``default`` if the file does not give it. The
        half-breadth of the element is half of it."""
        value = self._meta.get(name, {}).get("siding")
        return default if value is None else float(value)

    def keel_line(self):
        """The keel in the profile view, a straight line:
        ``((x0, y0), (x1, y1))`` in inches, from ``[keel]`` of the meta data
        file (``from`` and ``to``: the station and the height above the
        datum), or None if the file has none. A station that is not in the
        table is a ValueError."""
        keel = self._meta.get("keel")
        if not keel or "from" not in keel or "to" not in keel:
            return None
        positions = self.station_positions()
        ends = []
        for end in ("from", "to"):
            station = keel[end]["station"]
            if station not in positions:
                raise ValueError("[keel] %s: unknown station %r" % (end, station))
            ends.append((positions[station], float(keel[end]["height"])))
        return tuple(ends)

    def keel_point_at(self, station: str):
        """The keel point of the body line of ``station``: ``(half siding,
        height)`` in inches, the height is that of the keel line
        (``keel_line``) at the x of the station; None if the file gives no
        keel line or the station is beyond its ends. The half siding is half
        of ``siding("keel")`` (0 if the file does not give it). The body line
        of a station with a keel point goes down to it."""
        line = self.keel_line()
        if line is None:
            return None
        (x0, y0), (x1, y1) = line
        x = self.station_positions()[station]
        eps = 1e-9
        if not (min(x0, x1) - eps <= x <= max(x0, x1) + eps):
            return None
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return (self.siding("keel", 0.0) / 2, y0 + t * (y1 - y0))

    def plan_centerline_y(self):
        """(virtual) The y of the centerline of the plan view, where the
        half-breadths are measured from: the second of ``grid_y_origins``, or
        None if the sheet has only one view."""
        origins = self.grid_y_origins()
        return origins[1] if len(origins) > 1 else None

    def keel_profile_line(self):
        """The keel in the profile view: ``[(x0, y0), (x1, y1)]`` from the
        ``[keel]`` line, or None if the file gives none."""
        line = self.keel_line()
        return None if line is None else list(line)

    def rabbet_profile_line(self):
        """The rabbet in the profile view: the polyline of the row
        ``height_row`` of ``[rabbet]`` (the heights above the datum at the
        stations that have them), or None if the file gives no such row."""
        row = self._meta.get("rabbet", {}).get("height_row")
        return None if row is None else self.loft_line_n(self.line_to_index(row))

    def _plan_line(self, profile: list, siding_name: str):
        """The plan view of an element of a constant siding: a line at half
        the siding off the plan centerline, over the x of its profile line."""
        y0 = self.plan_centerline_y()
        if profile is None or y0 is None:
            return None
        y = y0 + self.siding(siding_name, 0.0) / 2
        return [(x, y) for x, _ in profile]

    def keel_plan_line(self):
        """The keel in the plan view (see ``_plan_line``), or None."""
        return self._plan_line(self.keel_profile_line(), "keel")

    def rabbet_plan_line(self):
        """The rabbet in the plan view, or None if the file gives no rabbet:
        the polyline of the row ``breadth_row`` of ``[rabbet]`` if it has
        one (like the other half-breadth rows, shifted by ``base_offset``),
        else a line of the constant ``siding`` (see ``_plan_line``)."""
        row = self._meta.get("rabbet", {}).get("breadth_row")
        if row is not None:
            return self.loft_line_n(self.line_to_index(row))
        return self._plan_line(self.rabbet_profile_line(), "rabbet")

    def plot_keel_and_rabbet(
        self, dxf: object, profile: bool = True, plan: bool = True
    ):
        """Draw the keel and the rabbet lines that the meta data file gives
        into ``dxf``: in the profile view (``profile``) and in the plan view
        (``plan``). Lines the file does not give are not drawn."""
        lines = []
        if profile:
            lines += [self.keel_profile_line(), self.rabbet_profile_line()]
        if plan:
            lines += [self.keel_plan_line(), self.rabbet_plan_line()]
        for line in lines:
            if line:
                dxf.add_red_polyline(line)

    def waterlines_positions(self):
        """(virtual) Return a dictionary: ``{name: height}``. From
        ``[waterlines]`` of the meta data file, if any."""
        if "waterlines" in self._meta:
            return {
                k: float(v["height"]) for k, v in self._meta["waterlines"].items()
            }
        print("TODO: please define waterline_positions()")
        return {}

    def diagonals_positions(self):
        """(virtual) The diagonals of the body plan: ``{name: (y0, x1, y1)}``,
        inches, heights above the base line. A diagonal is the straight line
        from the point ``(0, y0)`` on the centerline through the point
        ``(x1, y1)``; the table gives, per station, the distance along it from
        ``(0, y0)`` to the hull. From ``[diagonals]`` of the meta data file;
        the default is no diagonals."""
        return {
            name: (float(d["from"][1]), float(d["through"][0]), float(d["through"][1]))
            for name, d in self._meta.get("diagonals", {}).items()
        }

    def diagonal_row(self, name: str) -> str:
        """(virtual) The name of the table row with the distances of the
        diagonal ``name`` (a key of ``diagonals_positions``). The default is
        the same name."""
        return self._meta.get("diagonals", {}).get(name, {}).get("row", name)

    def offset_sign(self, station: str, line: str):
        """Returns either 1 or -1
        The function is used if offsets are negative below waterline

        {
            "B 3" : [ "33" , "20", ... ],
        }
        """
        if not line in self._under_waterline:
            return 1
        under = self._under_waterline[line]
        return -1 if station in under else 1

    def base_offset(self, line_name: str):
        """(virtual) Returns the vertical offset for the given line"""
        return 0

    def loft_line_n(self, n: int):
        """Return the polyline ``[(x, y), ...]`` for the n-th table row.

        x is the station position, y is the offset in inches (negated by
        ``offset_sign``, shifted by ``base_offset``). Stations with an empty
        cell are skipped. Points keep the column order of the CSV.
        """
        line_offsets = self._too.loc[n]
        stations = self.station_positions()

        poly_line = list()
        line_name = line_offsets["#"]
        for pos in stations:
            offset = line_offsets[pos]
            if type(offset) is str:
                s = self.offset_sign(pos, line_name)
                off = self.base_offset(line_name)
                poly_line.append(
                    (stations[pos], s * self.offset_to_inches(offset) + off)
                )

        return poly_line

    def loft_line_n_runs(self, n: int):
        """Like ``loft_line_n`` but a station with an empty cell breaks the
        line: returns a list of polylines, one for each run of consecutive
        stations (in the column order) that have the cell, so the line is not
        drawn across the stations where it does not exist (e.g. a waterline
        above the sheer). Runs of one point are dropped."""
        line_offsets = self._too.loc[n]
        stations = self.station_positions()
        line_name = line_offsets["#"]
        runs = [[]]
        for pos in stations:
            offset = line_offsets[pos]
            if type(offset) is str:
                s = self.offset_sign(pos, line_name)
                off = self.base_offset(line_name)
                runs[-1].append(
                    (stations[pos], s * self.offset_to_inches(offset) + off)
                )
            elif runs[-1]:
                runs.append([])
        return [r for r in runs if len(r) > 1]

    def loft_line_n_sorted(self, n: int):
        """Like ``loft_line_n`` but the points are sorted by x."""

        def first(t: tuple):
            return t[0]

        poly = self.loft_line_n(n)
        return sorted(poly, key=first)

    def loft_sheer(self):
        """return polyline to represent sheer line"""
        return self.loft_line_n(0)

    def loft_b3(self):
        """return polyline for B3"""
        return self.loft_line_n(1)

    def plot_grid(
        self,
        dxf: object,
        profile_end_x: float = None,
        body_centerline: tuple = None,
        body_buttocks: dict = None,
        body_diagonals: dict = None,
    ):
        """Draw the grid into ``dxf`` (a ``DXF`` object): central lines, one
        vertical line and label per station, waterlines and buttocks lines.

        ``profile_end_x`` - extend the base line (the first of
        ``grid_y_origins``) and the waterlines, with their right labels, to
        this x, e.g. to run through a body plan placed to the right of the
        profile view. Ignored if it is not beyond the last station.

        ``body_centerline`` - ``(x, bottom_y, top_y)``: draw the vertical
        centerline of a body plan there. See ``body_plan_grid_options``.

        ``body_buttocks`` - ``{name: [x, ...]}``: draw the buttock lines of the
        body plan as vertical lines at these x, as high as ``body_centerline``
        (which must be given too).

        ``body_diagonals`` - ``{name: [((x, y), (x, y)), ...]}``: draw the
        diagonals of the body plan as lines with their names at the second
        point (``diagonal_segments``).
        """

        stations = self.station_positions()
        xx = stations.values()

        right = max(xx) + 12
        if profile_end_x is not None:
            right = max(right, profile_end_x)

        # Draw central line(s); the base line (the first one) is extended
        for i, y in enumerate(self.grid_y_origins()):
            y_right = right if i == 0 else max(xx) + 12
            dxf.add_grid_polyline([(min(xx) - 12, y), (y_right, y)])

        if body_centerline is not None:
            x, bottom_y, top_y = body_centerline
            dxf.add_grid_polyline([(x, bottom_y), (x, top_y)])
            dxf.text((x + 1, top_y - 2), "CL")
            for name, buttock_xs in (body_buttocks or {}).items():
                for bx in buttock_xs:
                    dxf.add_grid_polyline([(bx, bottom_y), (bx, top_y)])
                    dxf.text((bx + 1, top_y - 2), name)

        for name, segments in (body_diagonals or {}).items():
            for p0, p1 in segments:
                dxf.add_grid_polyline([p0, p1])
                dxf.text((p1[0] + 1, p1[1] + 1), name)

        # draw station lines
        bottom_y, top_y = self.drawing_area_vertical_borders()

        for x in xx:
            dxf.add_grid_polyline([(x, bottom_y), (x, top_y)])

        for y in self.grid_y_origins():
            # place labels offset-ed by (1,1) from the waterline and
            # the station vertical intersection
            for s, x in stations.items():
                dxf.text((x + 1, y + 1), s)

        # waterlines
        wl_right = right
        for wl, wl_y in self.waterlines_positions().items():
            print("Waterline: ", wl, "at", wl_y)
            dxf.add_grid_polyline([(min(xx) - 12, wl_y), (wl_right, wl_y)])
            dxf.text((min(xx) - 12 + 1, wl_y + 1), wl)
            dxf.text((wl_right - 1, wl_y + 1), wl)

        # buttocks
        buttocks_origin = 0
        if len(self.grid_y_origins()) > 1:
            buttocks_origin = self.grid_y_origins()[1]
        for wl, wl_y in self.buttocks_positions().items():
            print("Buttocks line: ", wl, "at", wl_y)
            wl_y += buttocks_origin
            dxf.add_grid_polyline([(min(xx) - 12, wl_y), (max(xx) + 12, wl_y)])
            dxf.text((min(xx) - 12 + 1, wl_y + 1), wl)
            dxf.text((max(xx) + 12 - 1, wl_y + 1), wl)

    def drawing_area_vertical_borders(self):
        """(virtual) return (bottom, top); ``vertical_borders`` of ``[sheet]``
        of the meta data file, if any"""
        borders = self._meta.get("sheet", {}).get("vertical_borders")
        return tuple(map(float, borders)) if borders else (-12 * 10, 12 * 10)

    def grid_y_origins(self):
        """(virtual) returns y-coordinate list of the horizontal lines in the
        grid; ``y_origins`` of ``[sheet]`` of the meta data file, if any"""
        origins = self._meta.get("sheet", {}).get("y_origins")
        return [float(y) for y in origins] if origins else [0.0]

    def loft_body_line(
        self, station_id: str, body_points: list, skip_missing: bool = False
    ):
        """return a polyline to represent a body line at the given station
        loft a body plan line
        station_id - e.g. "5"
        body_points - list of (breadth, height) pairs. Each item is either
            a line name (looked up in the table at station_id) or a number
            (inches, used as is), e.g.
            [("SHEER", "LWL to SHEER"), ("WL 1A", 9.0), (36.0, "BASE TO B-3")]
        A plain string is used as both the breadth and the height line name.
        skip_missing - skip points whose table cell is empty at this station
            instead of raising ValueError
        Points are (half-breadth, height).
        """
        return [
            (x, y)
            for x, y, _, _ in self._body_point_sources(
                station_id, body_points, skip_missing
            )
        ]

    def _body_point_sources(
        self, station_id: str, body_points: list, skip_missing: bool
    ) -> list:
        """The points of ``loft_body_line`` with their sources:
        ``[(x, y, breadth_source, height_source)]``, a source is the name of the
        table row or the number (inches) the coordinate comes from."""
        points = []

        for pp in body_points:
            if isinstance(pp, DiagonalPoint):
                try:
                    distance = self._offset_at(
                        self.breadth_line_to_index(pp.row), station_id, pp.row, False
                    )
                except ValueError:
                    if not skip_missing:
                        raise
                    continue
                x, y = pp.point(distance)
                points.append((x, y, pp.row, pp.row))
                continue
            if isinstance(pp, GhostPoint):
                x = self.second_offset_at(station_id, pp.row)
                if x is not None:
                    points.append((x, pp.height, pp.row + " (2nd)", pp.height))
                continue
            if type(pp) is tuple:
                breadth_line, height_line = pp
            else:
                breadth_line = height_line = pp
            try:
                if isinstance(breadth_line, str):
                    x = self.breadth_at(station_id, breadth_line)
                else:
                    x = float(breadth_line)
                if isinstance(height_line, str):
                    y = self.height_at(station_id, height_line)
                else:
                    y = float(height_line)
            except ValueError:
                if not skip_missing:
                    raise
                continue
            points.append((x, y, breadth_line, height_line))

        return points

    def loft_body_line_sources(self, station_id: str, body_points: list) -> list:
        """The body line of one station (no shift, half-breadth only) with the
        source of every coordinate: ``[(x, y, breadth_source, height_source)]``,
        from the top down. The points are those of ``loft_body_lines``: the
        ``body_points`` and the waterlines that are in the table. A source is
        the name of the table row or the number (inches) of the point.
        """
        points = self._body_point_sources(
            station_id,
            list(body_points)
            + self.waterline_body_points()
            + self.diagonal_body_points()
            + self.ghost_body_points(),
            True,
        )
        points.sort(key=lambda pt: -pt[1])
        return points

    def format_length(self, inches: float) -> str:
        """A length for a label, in the unit of the table (inches for the
        feet-inches-eighths tables), e.g. ``"500 mm"``."""
        factor = TableOfOffsets.UNITS[self._unit]
        if factor is None:
            return "%g in" % round(inches, 3)
        return "%g %s" % (round(inches / factor, 3), self._unit)

    def plot_annotated_body_line(
        self,
        dxf: object,
        station_id: str,
        body_points: list,
        text_height: float = 2.0,
        point_text_height: float = None,
    ):
        """Draw the body line of one station for checking the data: the
        polyline, its centerline, and next to every point a label
        ``n (breadth source, height source)``, e.g. ``3 (Breadth Deck, Height
        Deck)`` or ``7 (500 mm, Height Buttock I)``. n is the number of the
        point from the top. The coordinates are not shifted.

        The base line (y = 0) and the waterlines (``waterlines_positions``) are
        drawn as horizontal lines with their names on the left, the buttocks
        (``buttocks_positions``) as vertical lines with their names on the top.

        ``text_height`` is the height of the labels of the grid, ``point_text_height``
        the height of the point labels (default ``text_height``).
        """
        points = self.loft_body_line_sources(station_id, body_points)
        if not points:
            return
        if point_text_height is None:
            point_text_height = text_height

        def source(src):
            return src if isinstance(src, str) else self.format_length(src)

        xs = [x for x, _, _, _ in points]
        ys = [y for _, y, _, _ in points]
        waterlines = self.waterlines_positions()
        buttocks = self.buttocks_positions()
        y_min = min([0.0] + ys + list(waterlines.values()))
        y_max = max([0.0] + ys + list(waterlines.values()))
        left, right = -30.0, max(xs + list(buttocks.values())) + 10.0

        dxf.add_grid_polyline([(0, y_min - 10), (0, y_max + 10)])
        dxf.text((1, y_max + 10), "station " + station_id, height=text_height)

        # the base line and the waterlines, named on the left
        for name, y in [("baseline", 0.0)] + list(waterlines.items()):
            dxf.add_grid_polyline([(left, y), (right, y)])
            dxf.text(
                (left - 1, y + 0.5),
                "%s (%s)" % (name, self.format_length(y)),
                align="right",
                height=text_height,
            )

        # the buttocks, named on the top
        for name, x in buttocks.items():
            dxf.add_grid_polyline([(x, y_min - 10), (x, y_max + 10)])
            dxf.text(
                (x, y_max + 11),
                "%s (%s)" % (name, self.format_length(x)),
                align="center",
                height=text_height,
            )
        for name, segments in self.diagonal_segments().items():
            for p0, p1 in segments:
                dxf.add_grid_polyline([p0, p1])
                dxf.text((p1[0] + 1, p1[1] + 1), name, height=text_height)
        dxf.add_red_polyline([(x, y) for x, y, _, _ in points])
        for n, (x, y, breadth_src, height_src) in enumerate(points, 1):
            dxf.text(
                (x + 1, y + 0.5),
                "%d (%s, %s)" % (n, source(breadth_src), source(height_src)),
                height=point_text_height,
            )

    BODY_PLACEMENTS = ("raw", "max_breadth", "right")
    BODY_SIDES = ("half", "both", "split")

    def loft_body_lines(
        self,
        body_points: list,
        placement: str = "max_breadth",
        gap: float = 24.0,
        sides: str = None,
        bow_station: str = None,
        keel_link: bool = True,
    ):
        """Return ``{station: [polyline, ...]}``: the body lines of every station.

        ``body_points`` is as for ``loft_body_line``. The waterlines that are in
        the table are always added (``waterline_body_points``). Points whose
        table cell is
        empty (or not a plain offset) at a station are skipped. Every polyline
        is sorted from the top (sheer) down.

        ``sides`` - which halves are drawn. The default (None) is ``"split"``
        for ``placement="max_breadth"``, i.e. for a body plan in the middle of
        the profile view, and ``"half"`` otherwise (see ``body_plan_sides``):

        - ``"half"``: the half-breadth to the right of the centerline;
        - ``"both"``: both halves, mirrored about the centerline, as one
          polyline per station (right sheer, down to the keel, up to the left
          sheer);
        - ``"split"``: the usual body plan. Stations aft of the midship (the
          station with the greatest breadth) are drawn to the left of the
          centerline, stations forward of it to the right. The midship station
          is drawn on both sides. Which end is the bow is given by
          ``bow_station`` (or ``set_bow_station``); if neither is set, the bow
          is the end with the greater x in ``station_positions``.

        ``bow_station`` - overrides ``set_bow_station`` for this call.

        ``keel_link`` - join the lowest point of every body line (the keel) to
        the centerline with a horizontal segment (a point (0, y) is appended
        unless the lowest point is already on the centerline).

        ``placement`` - where the centerline of the body plan is put along x
        (heights are the same as in the profile view, so y is not changed):

        - ``"max_breadth"`` (default): on the station with the greatest
          breadth, i.e. in the middle of the profile view;
        - ``"right"``: ``gap`` inches to the right of the last station, clear
          of the profile view (the left half, if any, is clear as well);
        - ``"raw"``: no shift, the centerline is at x = 0.
        """
        if placement not in self.BODY_PLACEMENTS:
            raise ValueError(
                "unknown placement %r, expected one of %s"
                % (placement, self.BODY_PLACEMENTS)
            )
        sides = self.body_plan_sides(placement, sides)
        if sides not in self.BODY_SIDES:
            raise ValueError(
                "unknown sides %r, expected one of %s" % (sides, self.BODY_SIDES)
            )

        body_points = (
            list(body_points)
            + self.waterline_body_points()
            + self.diagonal_body_points()
            + self.ghost_body_points()
        )

        rabbet = self.rabbet_body_point()
        if rabbet and rabbet not in body_points:
            body_points.append(rabbet)

        positions = self.station_positions()
        if bow_station is None:
            bow_station = self._bow_station
        if bow_station is not None and bow_station not in positions:
            raise KeyError("unknown station: %r" % (bow_station,))
        halves = {}
        # the first body point is the sheer, the rabbet is given by
        # rabbet_body_point(); a station without it (an empty cell) has no
        # such point
        sheer_points = self._station_points(positions, body_points[:1])
        rabbet_points = self._station_points(positions, [rabbet] if rabbet else [])
        keel = self.keel_body_point()
        keel_points = self._station_points(positions, [keel] if keel else [])
        for station in positions:
            poly = self.loft_body_line(station, body_points, skip_missing=True)
            keel_pt = self.keel_point_at(station)
            if keel_pt is not None:
                poly.append(keel_pt)
            poly.sort(key=lambda pt: -pt[1])
            if keel_link and poly and poly[-1][0] != 0:
                poly.append((0.0, poly[-1][1]))
            halves[station] = poly

        widest = None
        if any(halves.values()):
            widest = max(
                (s for s in halves if halves[s]),
                key=lambda s: max(x for x, _ in halves[s]),
            )

        def mirrored(poly):
            return [(-x, y) for x, y in poly]

        lines = {}
        flags = {}  # station: (drawn on the left, drawn on the right)
        for station, poly in halves.items():
            if not poly:
                lines[station] = []
            elif sides == "half":
                flags[station] = (False, True)
                lines[station] = [poly]
            elif sides == "both":
                flags[station] = (True, True)
                left = mirrored(poly)[::-1]
                if poly[-1][0] == 0:
                    left = left[1:]  # do not repeat a point on the centerline
                lines[station] = [poly + left]
            else:
                # forward is toward the bow station; by default the greater x
                bow_x = positions[bow_station] if bow_station else float("inf")
                if bow_x == positions[widest]:
                    raise ValueError(
                        "the bow station %r is the widest station" % (bow_station,)
                    )
                bow_is_right = bow_x > positions[widest]
                forward = (positions[station] > positions[widest]) == bow_is_right
                if station == widest:
                    left_side = right_side = True
                else:
                    right_side = forward
                    left_side = not forward
                flags[station] = (left_side, right_side)
                lines[station] = []
                if left_side:
                    lines[station].append(mirrored(poly))
                if right_side:
                    lines[station].append(poly)

        sheer = self._joined_points(sheer_points, flags, positions)
        rabbet = self._joined_points(rabbet_points, flags, positions)
        keel = self._joined_points(keel_points, flags, positions)

        x0 = self.body_plan_origin_x(lines, placement, gap, widest)
        self.body_plan_centerline_x = x0
        if x0 != 0:
            lines = {
                s: [[(x + x0, y) for x, y in p] for p in polys]
                for s, polys in lines.items()
            }
            sheer = [[(x + x0, y) for x, y in p] for p in sheer]
            rabbet = [[(x + x0, y) for x, y in p] for p in rabbet]
            keel = [[(x + x0, y) for x, y in p] for p in keel]
        result = BodyLines(lines)
        result.sheer = sheer
        result.rabbet = rabbet
        result.keel = keel
        return result

    def _station_points(self, positions: dict, body_points: list) -> dict:
        """``{station: (breadth, height)}`` of the one point in ``body_points``
        (a list of at most one item) for the stations that have it in the
        table."""
        points = {}
        if body_points:
            for station in positions:
                pt = self.loft_body_line(station, body_points, skip_missing=True)
                if pt:
                    points[station] = pt[0]
        return points

    @staticmethod
    def _joined_points(points: dict, flags: dict, positions: dict) -> list:
        """Join the points of the consecutive stations (``{station: (x, y)}``)
        into one polyline per side of the centerline: ``flags`` is ``{station:
        (drawn on the left, drawn on the right)}``. Returns up to two
        polylines of at least two points."""
        lines = []
        for side in (0, 1):
            pts = [
                (-points[s][0] if side == 0 else points[s][0], points[s][1])
                for s in sorted(points, key=lambda st: positions[st])
                if flags.get(s, (False, False))[side]
            ]
            if len(pts) > 1:
                lines.append(pts)
        return lines

    def keel_body_point(self):
        """(virtual) The ``(breadth, height)`` point of a body line (as an
        item of ``body_points``) that is the keel, or None if the hull has no
        keel line. Its points of the consecutive stations make the keel line
        of the body plan. (Not to be confused with ``keel_link``, which joins
        the lowest point of a body line to the centerline.)"""
        return None

    def rabbet_body_point(self):
        """(virtual) The ``(breadth, height)`` point of a body line (as an
        item of ``body_points``) that is the rabbet, or None if the hull has
        no rabbet line. Its points of the consecutive stations make the rabbet
        line of the body plan. From ``[rabbet]`` of the meta data file if it
        has ``height_row``: (``breadth_row``, ``height_row``), or without
        ``breadth_row`` (half of ``siding``, ``height_row``), the
        half-breadth being 0 without a siding."""
        rabbet = self._meta.get("rabbet", {})
        if "height_row" not in rabbet:
            return None
        breadth = rabbet.get("breadth_row", self.siding("rabbet", 0.0) / 2)
        return (breadth, rabbet["height_row"])

    @staticmethod
    def body_plan_sides(placement: str, sides: str = None):
        """The sides to draw: ``sides`` if given, otherwise ``"split"`` for a
        body plan in the middle of the profile view (``"max_breadth"``) and
        ``"half"`` for the others."""
        if sides is not None:
            return sides
        return "split" if placement == "max_breadth" else "half"

    def body_plan_grid_options(
        self, lines: dict, sides: str = None, margin: float = 12.0
    ):
        """Keyword arguments for ``plot_grid`` for a body plan placed to the
        right of the profile view (``lines`` as returned by ``loft_body_lines``
        with ``placement="right"`` and the same ``sides``): the base line and
        the waterlines run through the body plan, its vertical centerline and
        its buttock lines (``buttocks_positions``) are drawn. The buttocks are
        on the right of the centerline for ``sides="half"``, on both sides
        otherwise.
        """
        polylines = self.body_polylines(lines)
        if not polylines or self.body_plan_centerline_x is None:
            return {}
        cl = self.body_plan_centerline_x
        xs = [x for p in polylines for x, _ in p]
        ys = [y for p in polylines for _, y in p]
        sides = self.body_plan_sides("right", sides)
        buttocks = {}
        for name, offset in self.buttocks_positions().items():
            buttocks[name] = [cl + offset]
            if sides != "half":
                buttocks[name].insert(0, cl - offset)
        return {
            "profile_end_x": max(xs) + margin,
            "body_centerline": (cl, min(ys) - margin, max(ys) + margin),
            "body_buttocks": buttocks,
            "body_diagonals": self.diagonal_segments(cl, sides != "half"),
        }

    def plot_body_plan_grid(self, dxf: object, lines: dict, margin: float = 12.0):
        """Draw the grid of a body plan alone (no profile view) into ``dxf``:
        the base line, the waterlines (``waterlines_positions``) with their
        names, the vertical centerline ``CL``, the buttock lines
        (``buttocks_positions``) and the diagonals (``diagonals_positions``). ``lines`` is as returned by
        ``loft_body_lines`` (its centerline is ``body_plan_centerline_x``). The
        buttocks are drawn on both sides of the centerline if any body line is
        to the left of it, otherwise on the right only.
        """
        polylines = self.body_polylines(lines)
        if not polylines or self.body_plan_centerline_x is None:
            return
        cl = self.body_plan_centerline_x
        xs = [x for p in polylines for x, _ in p]
        ys = [y for p in polylines for _, y in p]
        waterlines = self.waterlines_positions()
        base_y = self.grid_y_origins()[0]
        left = min(xs + [cl]) - margin
        right = max(xs + [cl]) + margin
        bottom = min(ys + [base_y]) - margin
        top = max(ys + list(waterlines.values())) + margin

        for name, y in [("baseline", base_y)] + list(waterlines.items()):
            dxf.add_grid_polyline([(left, y), (right, y)])
            dxf.text((left + 1, y + 1), name)
            dxf.text((right - 1, y + 1), name, align="right")

        dxf.add_grid_polyline([(cl, bottom), (cl, top)])
        dxf.text((cl + 1, top - 2), "CL")
        both = min(xs) < cl
        for name, offset in self.buttocks_positions().items():
            for bx in [cl + offset] + ([cl - offset] if both else []):
                dxf.add_grid_polyline([(bx, bottom), (bx, top)])
                dxf.text((bx + 1, top - 2), name)
        for name, segments in self.diagonal_segments(cl, both).items():
            for p0, p1 in segments:
                dxf.add_grid_polyline([p0, p1])
                dxf.text((p1[0] + 1, p1[1] + 1), name)

    def plot_body_lines(
        self,
        dxf: object,
        lines: dict,
        labels: bool = True,
        sheer: bool = True,
        rabbet: bool = True,
        keel: bool = True,
    ):
        """Draw the body lines (as returned by ``loft_body_lines``) into
        ``dxf``. With ``labels`` the station name is written above the top end
        of every body line. With ``sheer`` the sheer line is drawn too, see
        ``body_sheer_polylines``, with ``rabbet`` the rabbet line, see
        ``body_rabbet_polylines``, with ``keel`` the keel line, see
        ``body_keel_polylines``.
        """
        for station, polys in lines.items():
            for poly in polys:
                if not poly:
                    continue
                dxf.add_red_polyline(poly)
                if labels:
                    # the highest point; the polylines run from the top down
                    x, y = max(poly, key=lambda pt: pt[1])
                    dxf.text((x, y + 1), station, align="center")
        if sheer:
            for poly in self.body_sheer_polylines(lines):
                dxf.add_red_polyline(poly)
        if rabbet:
            for poly in self.body_rabbet_polylines(lines):
                dxf.add_red_polyline(poly)
        if keel:
            for poly in self.body_keel_polylines(lines):
                dxf.add_red_polyline(poly)

    def body_sheer_polylines(self, lines: dict):
        """The sheer line of a body plan (``lines`` as returned by
        ``loft_body_lines``): the sheer points of the consecutive stations
        joined by a polyline, one polyline per side of the centerline: up to
        two for ``sides="split"`` or ``"both"``, one for ``"half"``. The sheer
        point is the first of the ``body_points``; a station whose table cell
        for it is empty is skipped. Returns ``[polyline, ...]``, each with at
        least 2 points.
        """
        return list(getattr(lines, "sheer", ()))

    def body_rabbet_polylines(self, lines: dict):
        """The rabbet line of a body plan (``lines`` as returned by
        ``loft_body_lines``): the rabbet points (``rabbet_body_point``) of the
        consecutive stations joined by a polyline, one per side of the
        centerline, as ``body_sheer_polylines``. Empty if the model has no
        rabbet."""
        return list(getattr(lines, "rabbet", ()))

    def body_keel_polylines(self, lines: dict):
        """The keel line of a body plan (``lines`` as returned by
        ``loft_body_lines``): the keel points (``keel_body_point``) of the
        consecutive stations joined by a polyline, one per side of the
        centerline, as ``body_sheer_polylines``. Empty if the model has no
        keel point."""
        return list(getattr(lines, "keel", ()))

    @staticmethod
    def body_polylines(lines: dict):
        """Flatten the result of ``loft_body_lines`` to a list of polylines."""
        return [p for polys in lines.values() for p in polys if p]

    def body_plan_origin_x(
        self, lines: dict, placement: str, gap: float = 24.0, widest: str = None
    ):
        """x position of the body plan centerline for the given placement.

        ``lines`` are the body lines relative to the centerline
        (``{station: [polyline, ...]}``), ``widest`` is the station with the
        greatest breadth.
        """
        positions = self.station_positions()
        if placement == "max_breadth":
            return positions[widest] if widest is not None else 0.0
        if placement == "right":
            xs = [x for polys in lines.values() for p in polys for x, _ in p]
            left_extent = -min(xs) if xs and min(xs) < 0 else 0.0
            return max(positions.values()) + gap + left_extent
        return 0.0

    def waterline_row(self, name: str) -> str:
        """(virtual) The name of the table row with the half-breadths of the
        waterline ``name`` (a key of ``waterlines_positions``). The default is
        the same name (``row`` in ``[waterlines]`` of the meta data file)."""
        return self._meta.get("waterlines", {}).get(name, {}).get("row", name)

    def waterline_body_points(self) -> list:
        """The waterlines as points of a body line: ``[(breadth_row, height)]``
        for every waterline of ``waterlines_positions`` that has its row
        (``waterline_row``) in the table. The half-breadth is from the table
        and the height is the position of the waterline."""
        rows = set(self._too["#"])
        return [
            (self.waterline_row(name), height)
            for name, height in self.waterlines_positions().items()
            if self.waterline_row(name) in rows
        ]

    def diagonal_extension(self):
        """(virtual) How far (inches, along the line) the diagonals are drawn
        beyond the farthest hull point of the table. The default ``None``
        draws them up to their second point ``(x1, y1)``."""
        return None

    def diagonal_segments(self, centerline_x: float = 0.0, both: bool = False):
        """The diagonals as line segments for drawing: ``{name: [((x, y),
        (x, y)), ...]}``, from ``(centerline_x, y0)`` to the second point of
        the diagonal, plus the mirror image about the centerline if ``both``.

        With ``diagonal_extension()`` the end is that far beyond the farthest
        hull point of the diagonal in the table (the second point if the
        diagonal is not in the table).
        """
        extension = self.diagonal_extension()
        ends = {}
        if extension is not None:
            positions = self.station_positions()
            for point in self.diagonal_body_points():
                points = self._station_points(positions, [point])
                if points:
                    far = max(abs(b) for b, _ in points.values()) / point._ux
                    ends[point.row] = point.point(far + extension)
        segments = {}
        for name, (y0, x1, y1) in self.diagonals_positions().items():
            x1, y1 = ends.get(self.diagonal_row(name), (x1, y1))
            segments[name] = [((centerline_x, y0), (centerline_x + x1, y1))]
            if both:
                segments[name].append(((centerline_x, y0), (centerline_x - x1, y1)))
        return segments

    def loft_diagonal_plan_lines(self, origin_y: float = None):
        """The diagonals in the plan view: ``{name: polyline}``, one point per
        station that has the diagonal in the table. x is the station position;
        the half-breadth of the hull point of the diagonal (see
        ``DiagonalPoint``) is drawn *below* the centerline of the plan view,
        i.e. y = ``origin_y`` - half-breadth, opposite to the waterlines and
        the sheer, which are above it.

        ``origin_y`` - the y of the plan view centerline; the default is the
        second of ``grid_y_origins()`` (0 if there is only one).
        """
        if origin_y is None:
            origins = self.grid_y_origins()
            origin_y = origins[1] if len(origins) > 1 else 0.0
        positions = self.station_positions()
        names = {self.diagonal_row(name): name for name in self.diagonals_positions()}
        lines = {}
        for point in self.diagonal_body_points():
            points = self._station_points(positions, [point])
            poly = [
                (positions[s], origin_y - points[s][0])
                for s in positions
                if s in points
            ]
            if poly:
                lines[names[point.row]] = poly
        return lines

    def plot_diagonal_plan_lines(self, dxf: object, labels: bool = True):
        """Draw ``loft_diagonal_plan_lines`` into ``dxf``; with ``labels`` the
        name of the diagonal is written at the first point."""
        for name, poly in self.loft_diagonal_plan_lines().items():
            dxf.add_red_polyline(poly)
            if labels:
                dxf.text((poly[0][0] + 1, poly[0][1] - 3), name)

    def diagonal_body_points(self) -> list:
        """The diagonals as points of a body line: a ``DiagonalPoint`` for
        every diagonal of ``diagonals_positions`` that has its row
        (``diagonal_row``) in the table."""
        rows = set(self._too["#"])
        return [
            DiagonalPoint(self.diagonal_row(name), y0, x1, y1)
            for name, (y0, x1, y1) in self.diagonals_positions().items()
            if self.diagonal_row(name) in rows
        ]

    def second_offset_at(self, station_id: str, line_id: str):
        """The second value of a cell ``offset1 and offset2`` of the row
        ``line_id`` at ``station_id`` in inches (breadth, no sign and no
        ``base_offset``), or ``None`` if the cell is empty or has one value."""
        if station_id not in self._too.columns:
            raise KeyError("unknown station: %r" % (station_id,))
        offset = self._too.loc[self.breadth_line_to_index(line_id), station_id]
        if type(offset) is not str:
            return None
        values = MULTI_VALUE_SEPARATOR.split(offset.strip())
        if len(values) < 2:
            return None
        return offset_to_inches(values[1], self._unit)

    def ghost_line(self):
        """(virtual) The "ghost line": ``(row, height)`` or ``None`` (default,
        no ghost line). It is at ``height`` inches above the base line, like a
        waterline, from the first to the last station that has a second value
        in the cells ``offset1 and offset2`` of the table row ``row``. It is
        drawn in the profile view (``loft_ghost_profile_line``) and in the body
        lines (``ghost_body_points``: a point at every station that has a
        second value) and in the plan view (``loft_ghost_plan_line``). From
        ``[ghost_line]`` of the meta data file, if any."""
        ghost = self._meta.get("ghost_line")
        return (ghost["row"], float(ghost["height"])) if ghost else None

    def ghost_body_points(self) -> list:
        """The ghost line as points of a body line: ``[GhostPoint]``, empty
        without a ghost line."""
        ghost = self.ghost_line()
        return [GhostPoint(*ghost)] if ghost else []

    def loft_ghost_plan_line(self) -> list:
        """The ghost line in the plan view: ``[(x, y), ...]``, x the station
        position, y the half-breadth (the second value) shifted by
        ``base_offset(row)``, like a waterline. Empty without a ghost line;
        stations without a second value are skipped."""
        ghost = self.ghost_line()
        if not ghost:
            return []
        row = ghost[0]
        poly = []
        for station, x in self.station_positions().items():
            breadth = self.second_offset_at(station, row)
            if breadth is not None:
                poly.append((x, breadth + self.base_offset(row)))
        return sorted(poly)

    def loft_ghost_profile_line(self) -> list:
        """The ghost line in the profile view: ``[(x, y), (x, y)]``, a
        horizontal segment at the height of the ghost line over the stations
        that have a second value in the row. Empty without a ghost line or
        without second values."""
        ghost = self.ghost_line()
        if not ghost:
            return []
        row, height = ghost
        xs = [
            x
            for station, x in self.station_positions().items()
            if self.second_offset_at(station, row) is not None
        ]
        return [(min(xs), height), (max(xs), height)] if xs else []

    def line_to_index(self, line_id: str) -> int:
        """Return the row index of the line named line_id (the "#" column)"""
        names = list(self._too["#"])
        if line_id not in names:
            raise KeyError("unknown line: %r" % (line_id,))
        return names.index(line_id)

    def breadth_line_to_index(self, line_id: str) -> int:
        """(virtual) "sheer" -> row index; default is lookup by name"""
        return self.line_to_index(line_id)

    def height_line_to_index(self, line_id: str) -> int:
        """(virtual) "rabbet" -> row index; default is lookup by name"""
        return self.line_to_index(line_id)

    def _offset_at(
        self, row: int, station_id: str, line_id: str, vertical: bool
    ) -> float:
        if station_id not in self._too.columns:
            raise KeyError("unknown station: %r" % (station_id,))
        offset = self._too.loc[row, station_id]
        if type(offset) is not str:
            raise ValueError(
                "no offset for line %r at station %r" % (line_id, station_id)
            )
        value = self.offset_to_inches(offset)
        if not vertical:
            # base_offset() positions lines on the drawing sheet (vertical only)
            return value
        return self.offset_sign(station_id, line_id) * value + self.base_offset(line_id)

    def breadth_at(self, station_id: str, line_id: str) -> float:
        """returns the half-breadth (inches) at the given station_id at the given line_id

        E.g. ("5", "sheer")
        """
        return self._offset_at(
            self.breadth_line_to_index(line_id), station_id, line_id, False
        )

    def height_at(self, station_id: str, line_id: str) -> float:
        """returns the height (inches) at the given station_id at the given line_id

        E.g. ("5", "WL 2")"""
        return self._offset_at(
            self.height_line_to_index(line_id), station_id, line_id, True
        )


class DXF:
    """Context manager that collects polylines and text and saves a DXF file.

    Usage::

        with DXF("out.dxf") as dxf:
            dxf.add_red_polyline([(0, 0), (10, 5)])

    The file is saved when the ``with`` block exits. Layers: ``grid``,
    ``red`` (lofted lines), ``text``.

    ``unit`` - the unit of the coordinates in the file (``OUTPUT_UNITS``,
    default ``"inch"``). The coordinates given to the methods are in inches;
    they are scaled to ``unit`` (and so are the text heights) and the unit is
    stored in the file (``$INSUNITS``).

    ACI colors
    1: Red
    2: Yellow
    3: Green
    4: Cyan
    5: Blue
    6: Magenta
    7: White or black
    """

    def __init__(self, output_dxf: str, unit: str = "inch"):
        if unit not in OUTPUT_UNITS:
            raise ValueError(
                "unknown output unit %r, expected one of %s" % (unit, OUTPUT_UNITS)
            )
        self._output_dxf = output_dxf
        self._unit = unit
        self._scale = 1.0 / TableOfOffsets.UNITS[unit]  # inches -> unit
        self._doc = ezdxf.new("R2010")
        self._doc.units = {
            "inch": ezdxf.units.IN,
            "ft": ezdxf.units.FT,
            "mm": ezdxf.units.MM,
            "cm": ezdxf.units.CM,
            "m": ezdxf.units.M,
        }[unit]
        self._msp = self._doc.modelspace()
        self._doc.layers.add(name="grid", color=6)
        self._doc.layers.add(name="red", color=1)
        self._doc.layers.add(name="text", color=3)

    def __enter__(self):
        # print("Enter with:", self._output_dxf)
        return self

    def __exit__(self, exception_type, exception_val, trace):
        # Exit logic here, called at exit of with block
        # print("Exit with:", self._output_dxf)
        # print(type(exception_type), type(exception_val), type(trace))
        # print("exception_type:", exception_type)
        # print("exception_val:", exception_val)

        self.close()
        if exception_val is not None:
            raise Exception(str(exception_val))

        return True

    def _scaled(self, poly: list) -> list:
        """The points (in inches) in the unit of the file"""
        return [(x * self._scale, y * self._scale) for x, y in poly]

    def add_polyline(self, poly: list):
        """Add a 2D polyline ``[(x, y), ...]`` to the default layer."""
        self._msp.add_polyline2d(self._scaled(poly))

    def add_red_polyline(self, poly: list):
        """Add a 2D polyline to the ``red`` layer."""
        self._msp.add_polyline2d(self._scaled(poly), dxfattribs={"layer": "red"})

    def add_grid_polyline(self, poly: list):
        """Add a 2D polyline to the ``grid`` layer."""
        self._msp.add_polyline2d(self._scaled(poly), dxfattribs={"layer": "grid"})

    def close(self):
        """Save the file (the directory is created if needed). Called
        automatically on leaving the ``with`` block."""
        if self._doc is not None:
            out_dir = os.path.dirname(self._output_dxf)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            self._doc.saveas(self._output_dxf)
            self._doc = None
            self._msp = None

    def text(self, xy: tuple, txt: str, align: str = "left", height: float = 1.0):
        """Add text to the ``text`` layer

        height - the height of the text in inches.

        align - ``"left"`` (``xy`` is the bottom left corner of the text),
        ``"center"`` (the middle of the bottom of the text) or ``"right"`` (the
        bottom right corner).

        # Using a predefined text style:
        msp.add_text(
            "Text Style Example: Liberation Serif",
            height=0.35,
            dxfattribs={"style": "LiberationSerif"}
        ).set_placement((2, 6), align=TextEntityAlignment.LEFT)
        """
        alignment = {
            "left": ezdxf.enums.TextEntityAlignment.LEFT,
            "center": ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER,
            "right": ezdxf.enums.TextEntityAlignment.BOTTOM_RIGHT,
        }[align]
        self._msp.add_text(
            txt, height=height * self._scale, dxfattribs={"layer": "text"}
        ).set_placement((xy[0] * self._scale, xy[1] * self._scale), align=alignment)
