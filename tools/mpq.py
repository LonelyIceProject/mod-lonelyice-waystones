"""Minimal StormLib wrapper (ctypes) for reading client MPQs and building patch MPQs."""
import ctypes
import os
from ctypes import wintypes

STORMLIB = os.environ.get(
    'STORMLIB_DLL',
    os.path.expandvars(r'%USERPROFILE%\scoop\apps\vcpkg\current\installed\x64-windows\bin\StormLib.dll'))

_lib = ctypes.WinDLL(STORMLIB)
HANDLE = ctypes.c_void_p
_lib.SFileGetFileSize.restype = ctypes.c_uint32
SFILE_INVALID_SIZE = 0xFFFFFFFF

STREAM_FLAG_READ_ONLY = 0x00000100
MPQ_CREATE_LISTFILE = 0x00100000
MPQ_CREATE_ATTRIBUTES = 0x00200000
MPQ_FILE_COMPRESS = 0x00000200
MPQ_FILE_REPLACEEXISTING = 0x80000000
MPQ_COMPRESSION_ZLIB = 0x02
MPQ_COMPRESSION_NEXT_SAME = 0xFFFFFFFF

# Archive paths are TCHAR; the vcpkg build may be UNICODE or ANSI, detect once.
_WIDE = None


def _open_archive(path, flags):
    global _WIDE
    h = HANDLE()
    for wide in ([_WIDE] if _WIDE is not None else [True, False]):
        arg = ctypes.c_wchar_p(path) if wide else ctypes.c_char_p(path.encode('mbcs'))
        if _lib.SFileOpenArchive(arg, 0, flags, ctypes.byref(h)):
            _WIDE = wide
            return h
    raise OSError(f'SFileOpenArchive failed for {path}: {ctypes.GetLastError()}')


def _tpath(path):
    return ctypes.c_wchar_p(path) if _WIDE else ctypes.c_char_p(path.encode('mbcs'))


def read_file(mpq_path, name):
    """Return file bytes from an MPQ, or None if the MPQ doesn't contain it."""
    mpq = _open_archive(mpq_path, STREAM_FLAG_READ_ONLY)
    try:
        if not _lib.SFileHasFile(mpq, name.encode()):
            return None
        hf = HANDLE()
        if not _lib.SFileOpenFileEx(mpq, name.encode(), 0, ctypes.byref(hf)):
            raise OSError(f'SFileOpenFileEx failed: {name}')
        try:
            size = _lib.SFileGetFileSize(hf, None)
            if size == SFILE_INVALID_SIZE:
                return None
            buf = ctypes.create_string_buffer(size)
            read = wintypes.DWORD()
            _lib.SFileReadFile(hf, buf, size, ctypes.byref(read), None)
            return buf.raw[:read.value]
        finally:
            _lib.SFileCloseFile(hf)
    finally:
        _lib.SFileCloseArchive(mpq)


def create_patch(mpq_path, files):
    """Create a new MPQ at mpq_path. files: {archived_name: local_path}."""
    if _WIDE is None:
        raise RuntimeError('call read_file first to detect TCHAR width')
    if os.path.exists(mpq_path):
        os.remove(mpq_path)
    h = HANDLE()
    if not _lib.SFileCreateArchive(_tpath(mpq_path), MPQ_CREATE_LISTFILE | MPQ_CREATE_ATTRIBUTES, 64, ctypes.byref(h)):
        raise OSError(f'SFileCreateArchive failed: {ctypes.GetLastError()}')
    try:
        for name, local in files.items():
            ok = _lib.SFileAddFileEx(h, _tpath(local), name.encode(),
                                     MPQ_FILE_COMPRESS | MPQ_FILE_REPLACEEXISTING,
                                     MPQ_COMPRESSION_ZLIB, MPQ_COMPRESSION_NEXT_SAME)
            if not ok:
                raise OSError(f'SFileAddFileEx failed for {name}: {ctypes.GetLastError()}')
        _lib.SFileCompactArchive(h, None, False)
    finally:
        _lib.SFileCloseArchive(h)
