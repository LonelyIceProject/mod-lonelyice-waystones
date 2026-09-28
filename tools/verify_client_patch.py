"""Print the patched Spell.dbc values from each locale's patch-<locale>-4.MPQ."""
import struct

import mpq
from make_client_patch import CLIENT, LOCALES, SPELL_INTS

for loc in LOCALES:
    d = mpq.read_file(rf'{CLIENT}\Data\{loc}\patch-{loc}-4.MPQ', r'DBFilesClient\Spell.dbc')
    _, n, f, rs, _ = struct.unpack_from('<4s4I', d, 0)
    st = d[20 + n * rs:]
    s = lambda o: st[o:st.index(b'\0', o)].decode()
    for i in range(n):
        r = struct.unpack_from('<%di' % f, d, 20 + i * rs)
        if r[0] in SPELL_INTS:
            print(loc, r[0], 'cd', r[29], 'dur', r[40], 'bp', r[80] + r[74], 'icon', r[133], '|', s(r[136]), '|', s(r[170]))
