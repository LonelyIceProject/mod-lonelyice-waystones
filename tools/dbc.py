"""Minimal WDBC reader for 3.3.5a client/server DBC files."""
import os
import struct

import mpq

# Game client folder (with Wow.exe) and the server's extracted data folder (DataDir).
CLIENT = os.environ.get('WOW_CLIENT', '')
SERVER_DBC = os.path.join(os.environ.get('WOW_SERVER_DATA', 'data'), 'dbc')


class Dbc:
    def __init__(self, data):
        magic, self.nrec, self.nfld, self.recsz, strsz = struct.unpack_from('<4s4I', data, 0)
        assert magic == b'WDBC', magic
        self._rec = data[20:20 + self.nrec * self.recsz]
        self._str = data[20 + self.nrec * self.recsz:]

    def rows(self):
        for i in range(self.nrec):
            yield Row(self, i * self.recsz)


class Row:
    def __init__(self, dbc, off):
        self._d, self._o = dbc, off

    def int(self, f):
        return struct.unpack_from('<i', self._d._rec, self._o + f * 4)[0]

    def uint(self, f):
        return struct.unpack_from('<I', self._d._rec, self._o + f * 4)[0]

    def float(self, f):
        return struct.unpack_from('<f', self._d._rec, self._o + f * 4)[0]

    def str(self, f):
        off = self.uint(f)
        end = self._d._str.index(b'\0', off)
        return self._d._str[off:end].decode('utf-8', 'replace')

    def loc(self, f):
        """First non-empty string of a 16-slot localized field (each locale MPQ fills its own slot)."""
        for slot in range(16):
            s = self.str(f + slot)
            if s:
                return s
        return ''


def server(name):
    with open(os.path.join(SERVER_DBC, name), 'rb') as f:
        return Dbc(f.read())


def client(locale, name):
    """DBC from the locale's highest-priority stock MPQ (our own patch-<loc>-4 is skipped)."""
    for rel in (rf'{locale}\patch-{locale}-3.MPQ', rf'{locale}\patch-{locale}-2.MPQ',
                rf'{locale}\patch-{locale}.MPQ', rf'{locale}\lichking-locale-{locale}.MPQ',
                rf'{locale}\expansion-locale-{locale}.MPQ', rf'{locale}\locale-{locale}.MPQ'):
        path = os.path.join(CLIENT, 'Data', rel)
        if os.path.exists(path):
            data = mpq.read_file(path, 'DBFilesClient\\' + name)
            if data:
                return Dbc(data)
    raise FileNotFoundError(f'{name} not found for {locale}')
