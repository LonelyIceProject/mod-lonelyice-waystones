"""Generate the Kirin Tor waycrystal network (FFXIV-style aetherytes) from the world DB.

Anchors are innkeepers and flight masters on the four continents. Anchors closer than MERGE_DIST
collapse into one waycrystal (innkeeper wins). Each crystal floats CRYSTAL_DIST yards in front of
its anchor NPC; players arrive between the anchor and the crystal.

Outputs (both locales are taken from the client's ruRU/enGB DBCs):
  - world SQL (data/sql/db-world): creature template, spawns and the custom_waystone table the server reads;
  - the client addon's Data.lua with names and world-map positions.

Re-run after changing anything here, then apply the SQL (worldserver also applies it on start).
"""
import math
import os
import shutil

import dbc
from worldmap import DALARAN_UNDERBELLY_Z, ROOT, World, lua_str, query

SQL_OUT = os.path.join(ROOT, 'data', 'sql', 'db-world', '2026_09_25_01_waystones.sql')
ADDON_DIR = os.path.join(ROOT, 'client', 'addons', 'KirinTorWaystones')
LUA_OUT = os.path.join(ADDON_DIR, 'Data.lua')
CLIENT_ADDON = os.path.join(dbc.CLIENT, r'Interface\AddOns\KirinTorWaystones')

# Keep in sync with custom_waystones.cpp
NPC_ENTRY = 9100001
GUID_BASE = 9100000
DISPLAY_ID = 17856          # Creature\QuestObjects\Creature_PowerCrystal (also worn by spawned 'Iron Dwarf Relic')
DISPLAY_SCALE = 1.0

MERGE_DIST = 150.0
CRYSTAL_DIST = 3.5
CRYSTAL_HOVER = 1.0
ARRIVAL_DIST = 1.8

NPCFLAG_FLIGHTMASTER = 0x2000
NPCFLAG_INNKEEPER = 0x10000
EXCLUDED_ZONES = {
    4298,   # Plaguelands: The Scarlet Enclave (death knight start, phased)
    4197,   # Wintergrasp (PvP battlefield)
}
MERGE_SAME_AREA_DIST = 600.0
DUP_SUFFIX = {'ruRU': ('трактир', 'полёты'), 'enGB': ('Inn', 'Flights')}


GOSSIP_TEXT = {
    'ruRU': 'Кристалл гудит тайной магией Кирин-Тора. Путник, коснувшийся его, может перенестись '
            'к любому кристаллу сети, на который он уже настроен.',
    'enGB': 'The crystal hums with the arcane power of the Kirin Tor. A traveller who has touched it '
            'may translocate to any crystal of the network they are attuned to.',
}

NAMES = {
    'ruRU': ('Путевой кристалл', 'Сеть транслокации Кирин-Тора'),
    'enGB': ('Waycrystal', 'Kirin Tor Translocation Network'),
}


def main():
    world = World()
    area_names = {loc: {r.int(0): r.loc(11) for r in dbc.client(loc, 'AreaTable.dbc').rows()} for loc in NAMES}
    taxi = [(r.int(1), r.float(2), r.float(3), {loc: None for loc in NAMES}, r.int(0))
            for r in dbc.server('TaxiNodes.dbc').rows()]
    taxi_names = {loc: {r.int(0): r.loc(5) for r in dbc.client(loc, 'TaxiNodes.dbc').rows()} for loc in NAMES}

    rows = query(f'''
        SELECT c.guid, c.map, c.position_x, c.position_y, c.position_z, c.orientation, t.npcflag
        FROM creature c JOIN creature_template t ON t.entry = c.id
        WHERE c.map IN (0, 1, 530, 571) AND (c.phaseMask & 1) AND (t.npcflag & {NPCFLAG_INNKEEPER | NPCFLAG_FLIGHTMASTER})
          AND c.guid NOT IN (SELECT guid FROM game_event_creature)
        ORDER BY c.guid''')

    anchors = []
    for guid, m, x, y, z, o, flag in rows:
        m, x, y, z, o, flag = int(m), float(x), float(y), float(z), float(o), int(flag)
        area, zone = world.locate(m, x, y, z)
        if not zone or zone in EXCLUDED_ZONES:
            continue
        if zone == 4395 and z < DALARAN_UNDERBELLY_Z:
            continue
        inn = bool(flag & NPCFLAG_INNKEEPER)
        anchors.append(dict(guid=int(guid), map=m, x=x, y=y, z=z, o=o, inn=inn, area=area, zone=zone))

    # Innkeepers first so they win merges; stable by guid otherwise
    anchors.sort(key=lambda a: (not a['inn'], a['guid']))
    kept = []
    for a in anchors:
        def near(k):
            if k['map'] != a['map']:
                return False
            d = math.dist((k['x'], k['y']), (a['x'], a['y']))
            same_area = k['area'] == a['area'] and a['area'] != a['zone']
            return d < MERGE_DIST or (same_area and d < MERGE_SAME_AREA_DIST)
        if any(near(k) for k in kept):
            continue
        kept.append(a)

    # Stable ids: order by continent, zone, position
    kept.sort(key=lambda a: (a['map'], a['zone'], round(a['x']), round(a['y'])))

    def nearest_taxi(a):
        best = None
        for m, x, y, _n, tid in taxi:
            if m == a['map']:
                d = math.dist((x, y), (a['x'], a['y']))
                if d < 60 and (best is None or d < best[0]):
                    best = (d, tid)
        return best and best[1]

    waystones = []
    for i, a in enumerate(kept, 1):
        names = {}
        tid = nearest_taxi(a)
        for loc in NAMES:
            if a['area'] and a['area'] != a['zone']:
                name = area_names[loc][a['area']]
            elif tid:
                name = taxi_names[loc][tid].split(',')[0].strip()
            else:
                name = area_names[loc][a['zone']]
            names[loc] = name.strip()
        zp = world.zone_pos(a['map'], a['zone'], a['x'], a['y'])
        cp = world.continent_pos(a['map'], a['x'], a['y'])
        ox, oy = math.cos(a['o']), math.sin(a['o'])
        waystones.append(dict(
            id=i, map=a['map'], zone=a['zone'], area=a['area'], inn=a['inn'],
            cx=a['x'] + ox * CRYSTAL_DIST, cy=a['y'] + oy * CRYSTAL_DIST, cz=a['z'] + CRYSTAL_HOVER,
            co=(a['o'] + math.pi) % (2 * math.pi),
            dx=a['x'] + ox * ARRIVAL_DIST, dy=a['y'] + oy * ARRIVAL_DIST, dz=a['z'] + 0.5,
            do=a['o'],
            name=names, zone_name={loc: area_names[loc][a['zone']] for loc in NAMES},
            wma=zp, cont=cp))

    # Same display name twice in one zone: tell them apart by anchor kind, then by number
    for loc in NAMES:
        seen = {}
        for w in waystones:
            seen.setdefault((w['zone'], w['name'][loc]), []).append(w)
        for group in seen.values():
            if len(group) < 2:
                continue
            for w in group:
                kind = DUP_SUFFIX[loc][0 if w['inn'] else 1]
                same = [g for g in group if g['inn'] == w['inn']]
                if len(same) == 1:
                    w['name'][loc] += f' ({kind})'
                elif len(same) == len(group):
                    w['name'][loc] += f' ({same.index(w) + 1})'
                else:
                    w['name'][loc] += f' ({kind} {same.index(w) + 1})'

    write_sql(waystones)
    write_lua(waystones)
    print(f'{len(anchors)} anchors -> {len(waystones)} waycrystals')
    shutil.copytree(ADDON_DIR, CLIENT_ADDON, dirs_exist_ok=True)
    print(f'  {SQL_OUT}\n  {LUA_OUT}\n  installed to {CLIENT_ADDON}')


def esc(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")


def write_sql(ws):
    ru, en = NAMES['ruRU'], NAMES['enGB']
    lines = [
        '-- GENERATED by tools/make_waystones.py - do not edit, re-run the generator instead.',
        '-- Kirin Tor waycrystals: FFXIV-style teleport network (see src/custom_waystones.cpp).',
        '',
        f'DELETE FROM `creature_template` WHERE `entry` = {NPC_ENTRY};',
        'INSERT INTO `creature_template` (`entry`, `name`, `subname`, `IconName`, `minlevel`, `maxlevel`, `faction`, '
        '`npcflag`, `unit_class`, `unit_flags`, `type`, `flags_extra`, `HealthModifier`, `ScriptName`) VALUES',
        f"({NPC_ENTRY}, '{esc(en[0])}', '{esc(en[1])}', 'Interact', 80, 80, 35, 1, 1, 768, 10, 2, 100, "
        "'npc_custom_waystone');",
        f'DELETE FROM `creature_template_locale` WHERE `entry` = {NPC_ENTRY};',
        'INSERT INTO `creature_template_locale` (`entry`, `locale`, `Name`, `Title`) VALUES',
        f"({NPC_ENTRY}, 'ruRU', '{esc(ru[0])}', '{esc(ru[1])}');",
        f'DELETE FROM `creature_template_model` WHERE `CreatureID` = {NPC_ENTRY};',
        'INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`) VALUES',
        f'({NPC_ENTRY}, 0, {DISPLAY_ID}, {DISPLAY_SCALE}, 1);',
        f'DELETE FROM `creature_template_movement` WHERE `CreatureId` = {NPC_ENTRY};',
        'INSERT INTO `creature_template_movement` (`CreatureId`, `Ground`, `Swim`, `Flight`, `Rooted`) VALUES',
        f'({NPC_ENTRY}, 0, 0, 1, 1);',
        f'DELETE FROM `npc_text` WHERE `ID` = {NPC_ENTRY};',
        'INSERT INTO `npc_text` (`ID`, `text0_0`, `Probability0`) VALUES',
        f"({NPC_ENTRY}, '{esc(GOSSIP_TEXT['enGB'])}', 1);",
        f'DELETE FROM `npc_text_locale` WHERE `ID` = {NPC_ENTRY};',
        'INSERT INTO `npc_text_locale` (`ID`, `Locale`, `Text0_0`) VALUES',
        f"({NPC_ENTRY}, 'ruRU', '{esc(GOSSIP_TEXT['ruRU'])}');",
        '',
        'DROP TABLE IF EXISTS `custom_waystone`;',
        'CREATE TABLE `custom_waystone` (',
        '  `id` INT UNSIGNED NOT NULL,',
        '  `map` SMALLINT UNSIGNED NOT NULL,',
        '  `zone` INT UNSIGNED NOT NULL,',
        '  `continent` INT UNSIGNED NOT NULL COMMENT \'WorldMapArea id of the continent map showing it\',',
        '  `x` FLOAT NOT NULL, `y` FLOAT NOT NULL, `z` FLOAT NOT NULL, `o` FLOAT NOT NULL,',
        '  `name_en` VARCHAR(100) NOT NULL, `name_ru` VARCHAR(100) NOT NULL,',
        '  `zone_en` VARCHAR(100) NOT NULL, `zone_ru` VARCHAR(100) NOT NULL,',
        '  PRIMARY KEY (`id`)',
        ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT=\'Waycrystal arrival points (tools/make_waystones.py)\';',
        'INSERT INTO `custom_waystone` (`id`, `map`, `zone`, `continent`, `x`, `y`, `z`, `o`, `name_en`, `name_ru`, `zone_en`, `zone_ru`) VALUES',
    ]
    lines.append(',\n'.join(
        f"({w['id']}, {w['map']}, {w['zone']}, {w['cont'][0]}, {w['dx']:.3f}, {w['dy']:.3f}, {w['dz']:.3f}, {w['do']:.4f}, "
        f"'{esc(w['name']['enGB'])}', '{esc(w['name']['ruRU'])}', "
        f"'{esc(w['zone_name']['enGB'])}', '{esc(w['zone_name']['ruRU'])}')" for w in ws) + ';')
    lines += [
        '',
        f'DELETE FROM `creature` WHERE `id` = {NPC_ENTRY} OR `guid` BETWEEN {GUID_BASE} AND {GUID_BASE + 9999};',
        'INSERT INTO `creature` (`guid`, `id`, `map`, `zoneId`, `areaId`, `spawnMask`, `phaseMask`, `position_x`, '
        '`position_y`, `position_z`, `orientation`, `spawntimesecs`, `wander_distance`, `MovementType`) VALUES',
    ]
    lines.append(',\n'.join(
        f"({GUID_BASE + w['id']}, {NPC_ENTRY}, {w['map']}, {w['zone']}, {w['area']}, 1, 1, "
        f"{w['cx']:.3f}, {w['cy']:.3f}, {w['cz']:.3f}, {w['co']:.4f}, 300, 0, 0)" for w in ws) + ';')
    os.makedirs(os.path.dirname(SQL_OUT), exist_ok=True)
    with open(SQL_OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def write_lua(ws):
    out = ['-- GENERATED by tools/make_waystones.py - do not edit.',
           '-- id = { zoneMapID, floor, x, y, continentMapID, cx, cy, name_en, name_ru, zone_en, zone_ru, inn }',
           'KTW_DATA = {']
    for w in ws:
        zm, fl, x, y = w['wma'] or (0, 0, 0, 0)
        cm, cx, cy = w['cont']
        out.append(f"  [{w['id']}] = {{ {zm}, {fl}, {x:.4f}, {y:.4f}, {cm}, {cx:.4f}, {cy:.4f}, "
                   f"{lua_str(w['name']['enGB'])}, {lua_str(w['name']['ruRU'])}, "
                   f"{lua_str(w['zone_name']['enGB'])}, {lua_str(w['zone_name']['ruRU'])}, "
                   f"{'true' if w['inn'] else 'false'} }},")
    out.append('}')
    os.makedirs(os.path.dirname(LUA_OUT), exist_ok=True)
    with open(LUA_OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()
