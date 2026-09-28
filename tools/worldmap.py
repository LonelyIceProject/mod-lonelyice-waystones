"""World DB access and world -> world-map coordinate helpers shared by the map generators."""
import contextlib
import decimal
import os
import pathlib
import sqlite3
import struct
import subprocess

import dbc

# Repository root; the server's data folder (DataDir) and world database come from the environment.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPS = os.path.join(os.environ.get('WOW_SERVER_DATA', 'data'), 'maps')
WORLD_DB = os.environ.get('WOW_WORLD_DB', os.path.join('db', 'world.sqlite'))

CONTINENT_WMA = {0: 14, 1: 13, 530: 466, 571: 485}
# Cities built as WMOs report the terrain's zone underneath; claim points inside the city's
# world-map rectangle within this height band instead: zone -> (map, min z, max z)
WMO_CITIES = {
    1537: (0, -1e9, 1e9),     # Ironforge
    1497: (0, -1e9, 0.0),     # Undercity (below Ruins of Lordaeron)
    4395: (571, 500.0, 1e9),  # Dalaran (floating over Crystalsong Forest)
}
DALARAN = 4395
DALARAN_UNDERBELLY_Z = 640.0
DALARAN_UNDERBELLY_FLOOR = 2


def mysql_text(v):
    """Value as the mysql client prints it with -B (FLOAT columns: 6 significant digits)."""
    if v is None:
        return 'NULL'
    if isinstance(v, float):
        text = format(struct.unpack('<f', struct.pack('<f', v))[0], '.6g')
        return format(decimal.Decimal(text), 'f') if 'e' in text else text
    return str(v)


def query(sql):
    if os.path.exists(WORLD_DB):
        with contextlib.closing(sqlite3.connect(pathlib.Path(WORLD_DB).as_uri() + '?mode=ro', uri=True)) as db:
            return [[mysql_text(v) for v in row] for row in db.execute(sql)]
    out = subprocess.run(['docker', 'exec', '-i', 'acore-mysql', 'mysql', '-uacore', '-pacore', '-N', '-B',
                          '--default-character-set=utf8mb4', 'acore_world'],
                         input=sql.encode(), capture_output=True, check=True).stdout
    return [line.split('\t') for line in out.decode('utf-8').splitlines() if line]


# ---------------------------------------------------------------- terrain area lookup (.map files)
_area_cache = {}


def area_at(map_id, x, y):
    gx, gy = int(32 - x / 533.33333), int(32 - y / 533.33333)
    key = (map_id, gx, gy)
    if key not in _area_cache:
        path = os.path.join(MAPS, f'{map_id:03}{gx:02}{gy:02}.map')
        grid = None
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = f.read()
            area_off = struct.unpack_from('<I', data, 12)[0]
            _fourcc, flags, grid_area = struct.unpack_from('<IHH', data, area_off)
            grid = grid_area if flags & 1 else struct.unpack_from('<256H', data, area_off + 8)
        _area_cache[key] = grid
    grid = _area_cache[key]
    if grid is None or isinstance(grid, int):
        return grid or 0
    lx, ly = int(16 * (32 - x / 533.33333)) & 15, int(16 * (32 - y / 533.33333)) & 15
    return grid[lx * 16 + ly]


def world_to_wma(r, x, y):
    left, right, top, bottom = (r.float(f) for f in (4, 5, 6, 7))
    return (left - y) / (left - right), (top - x) / (top - bottom)


class World:
    def __init__(self):
        self.areas = {r.int(0): r for r in dbc.server('AreaTable.dbc').rows()}
        self.wma = {r.int(0): r for r in dbc.server('WorldMapArea.dbc').rows()}
        self.wma_by_zone = {(r.int(1), r.int(2)): r for r in self.wma.values() if r.int(2)}
        self.transforms = [r for r in dbc.server('WorldMapTransforms.dbc').rows() if r.int(1) in CONTINENT_WMA]
        self.dungeon_maps = {r.int(0): r for r in dbc.server('DungeonMap.dbc').rows()}

    def floors_of(self, wma_row):
        """Floors of a floor-based world map; WorldMapArea names its default DungeonMap row, siblings share field 7."""
        first = self.dungeon_maps[wma_row.int(9)]
        return [f for f in self.dungeon_maps.values() if f.int(1) == first.int(1) and f.int(7) == first.int(7)]

    def zone_of(self, area_id):
        seen = 0
        while area_id and self.areas[area_id].int(2) and seen < 5:
            area_id, seen = self.areas[area_id].int(2), seen + 1
        return area_id

    def locate(self, m, x, y, z):
        """(area, zone) of a world position, with WMO cities claiming their own rectangle."""
        area = area_at(m, x, y)
        zone = self.zone_of(area)
        for city, (cmap, zmin, zmax) in WMO_CITIES.items():
            r = self.wma_by_zone[(cmap, city)]
            rect = [r.float(f) for f in (4, 5, 6, 7)]
            if r.float(4) == r.float(5):       # floor-based: take the union of its floors
                fl = self.floors_of(r)
                rect = [max(f.float(4) for f in fl), min(f.float(3) for f in fl),
                        max(f.float(6) for f in fl), min(f.float(5) for f in fl)]
            left, right, top, bottom = rect
            if m == cmap and right <= y <= left and bottom <= x <= top and zmin <= z <= zmax:
                area = zone = city
        return area, zone

    def zone_pos(self, m, zone, x, y, z=None):
        """(zone WorldMapArea id, floor, map x, map y) or None when the zone has no world map."""
        r = self.wma_by_zone.get((m, zone))
        if r is None:
            return None
        if r.float(4) == r.float(5):     # floor-based map (Dalaran): first floor containing the point
            floors = sorted(self.floors_of(r), key=lambda f: f.int(2))
            if zone == DALARAN and z is not None and z < DALARAN_UNDERBELLY_Z:
                floors = [f for f in floors if f.int(2) == DALARAN_UNDERBELLY_FLOOR]
            for f in floors:
                min_y, max_y, min_x, max_x = (f.float(i) for i in (3, 4, 5, 6))
                if min_y <= y <= max_y and min_x <= x <= max_x:
                    return r.int(0), f.int(2), (max_y - y) / (max_y - min_y), (max_x - x) / (max_x - min_x)
            return None
        mx, my = world_to_wma(r, x, y)
        return r.int(0), 0, mx, my

    def continent_pos(self, m, x, y):
        for t in self.transforms:
            if t.int(1) == m and t.float(2) <= x <= t.float(4) and t.float(3) <= y <= t.float(5):
                m, x, y = t.int(6), x + t.float(7), y + t.float(8)
                break
        cont = CONTINENT_WMA[m]
        mx, my = world_to_wma(self.wma[cont], x, y)
        return cont, mx, my


def lua_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
