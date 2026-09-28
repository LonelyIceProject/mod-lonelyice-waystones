"""Build Data/<locale>/patch-<locale>-4.MPQ for every client locale in LOCALES.

For each locale takes Spell.dbc from that locale's highest-priority MPQ, patches records and writes a
new patch MPQ (rebuilt from scratch each run). Numbers are shared; texts are per locale.
"""
import os
import struct

import mpq

CLIENT = os.environ.get('WOW_CLIENT', '')
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')

# Spell.dbc field indices (3.3.5a, see DBCStructure.h SpellEntry)
F_CASTING_TIME_INDEX = 28
F_RECOVERY_TIME = 29
F_DURATION_INDEX = 40
F_EFFECT_DIE_SIDES = 74
F_EFFECT_BASE_POINTS = 80
F_SPELL_ICON = 133
F_NAME, F_RANK, F_DESCRIPTION, F_TOOLTIP = 136, 153, 170, 187   # 16 locale slots each

DURATION_20S = 18       # SpellDuration.dbc id with 20000 ms
ICON_SPRINT = 516       # Interface\Icons\Ability_Rogue_Sprint (same icon as Mithril Spurs)

CAST_TIME_5S = 6        # SpellCastTimes.dbc id with 5000 ms
ICON_TELEPORT_DALARAN = 3167

SPRINT = 56354
TRANSLOCATION = 44080   # "Teleport: Zul'Aman Instance", reused by src/waystones.cpp

# Keep in sync with mod-lonelyice-qol src/sprint.cpp (server applies the same values for players)
SPELL_INTS = {
    SPRINT: {
        F_RECOVERY_TIME: 35000,
        F_DURATION_INDEX: DURATION_20S,
        F_EFFECT_BASE_POINTS: 50 - 1,   # client shows BasePoints + DieSides
        F_EFFECT_DIE_SIDES: 1,
        F_SPELL_ICON: ICON_SPRINT,
    },
    TRANSLOCATION: {
        F_CASTING_TIME_INDEX: CAST_TIME_5S,
        F_SPELL_ICON: ICON_TELEPORT_DALARAN,
    },
}

LOCALES = {
    'ruRU': {
        SPRINT: {
            F_NAME: 'Спринт',
            F_RANK: '',
            F_DESCRIPTION: 'Увеличивает скорость передвижения на $s1% на $d.',
            F_TOOLTIP: 'Скорость передвижения увеличена на $s1%.',
        },
        TRANSLOCATION: {
            F_NAME: 'Транслокация',
            F_RANK: '',
            F_DESCRIPTION: 'Перемещает вас к выбранному путевому кристаллу Кирин-Тора.',
            F_TOOLTIP: '',
        },
    },
    'enGB': {
        SPRINT: {
            F_NAME: 'Sprint',
            F_RANK: '',
            F_DESCRIPTION: 'Increases movement speed by $s1% for $d.',
            F_TOOLTIP: 'Movement speed increased by $s1%.',
        },
        TRANSLOCATION: {
            F_NAME: 'Translocation',
            F_RANK: '',
            F_DESCRIPTION: 'Translocates you to the chosen Kirin Tor waycrystal.',
            F_TOOLTIP: '',
        },
    },
}


def load_source(locale):
    for rel in (rf'{locale}\patch-{locale}-3.MPQ', rf'{locale}\patch-{locale}-2.MPQ', rf'{locale}\patch-{locale}.MPQ'):
        path = os.path.join(CLIENT, 'Data', rel)
        if os.path.exists(path):
            data = mpq.read_file(path, r'DBFilesClient\Spell.dbc')
            if data:
                print(f'  Spell.dbc taken from {rel}')
                return data
    raise SystemExit(f'Spell.dbc not found in {locale} client MPQs')


def patch_dbc(data, texts):
    magic, nrec, nfld, recsz, strsz = struct.unpack_from('<4s4I', data, 0)
    assert magic == b'WDBC' and nfld == 234, (magic, nfld)
    records = bytearray(data[20:20 + nrec * recsz])
    strings = bytearray(data[20 + nrec * recsz:])

    def add_string(s):
        if not s:
            return 0
        off = len(strings)
        strings.extend(s.encode('utf-8') + b'\0')
        return off

    index = {struct.unpack_from('<I', records, i * recsz)[0]: i for i in range(nrec)}
    for spell_id, ints in SPELL_INTS.items():
        base = index[spell_id] * recsz
        for field, value in ints.items():
            struct.pack_into('<i', records, base + field * 4, value)
        for field, text in texts.get(spell_id, {}).items():
            off = add_string(text)
            # The client reads its own locale's slot; write every slot to not depend on slot order
            for slot in range(16):
                struct.pack_into('<I', records, base + (field + slot) * 4, off)
        print(f'  patched spell {spell_id}')

    header = struct.pack('<4s4I', magic, nrec, nfld, recsz, len(strings))
    return header + bytes(records) + bytes(strings)


def main():
    for locale, texts in LOCALES.items():
        if not os.path.isdir(os.path.join(CLIENT, 'Data', locale)):
            print(f'{locale}: not installed, skipped')
            continue
        print(f'{locale}:')
        out_dir = os.path.join(WORK, locale)
        os.makedirs(out_dir, exist_ok=True)
        local = os.path.join(out_dir, 'Spell.dbc')
        with open(local, 'wb') as f:
            f.write(patch_dbc(load_source(locale), texts))
        out_mpq = os.path.join(CLIENT, 'Data', locale, f'patch-{locale}-4.MPQ')
        mpq.create_patch(out_mpq, {r'DBFilesClient\Spell.dbc': local})
        print(f'  wrote {out_mpq} ({os.path.getsize(out_mpq) // 1024} KB)')


if __name__ == '__main__':
    main()
