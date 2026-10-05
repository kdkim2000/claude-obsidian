"""Opt-in native-Windows emulation of directory-descriptor operations.

POSIX hosts pin directories with ``os.open(O_DIRECTORY)`` and operate relative
to those descriptors (``dir_fd=``).  Native Windows has neither.  When the
operator sets ``CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES=1`` on Windows, modules
that rebind their ``os`` name to :data:`os_proxy` get *virtual* directory
handles: small integers mapped to paths.

Guarantee level (deliberately weaker than POSIX): each directory open verifies
with ``lstat`` that the target is a plain directory (no symlink or junction),
but a handle does not hold the directory open, so a concurrent swap between
checks is not prevented.  This is acceptable for a single-user local vault and
is NOT a substitute for the descriptor-confined POSIX/WSL mode.

When the opt-in is absent the proxy behaves exactly like :mod:`os`, apart from
a safe ``kill(pid, 0)``: on Windows the stdlib implementation terminates the
target process instead of probing it.
"""

from __future__ import annotations

import errno
import itertools
import os as _os
import stat as _stat
from typing import Any

ENV_FLAG = "CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES"

# Virtual open flags; never reach the C runtime.
_O_DIRECTORY = 0x10000000
_O_NOFOLLOW = 0x20000000
_VIRTUAL_FLAGS = _O_DIRECTORY | _O_NOFOLLOW
_HANDLE_BASE = 1 << 30

_REPARSE_TAGS = frozenset(
    {
        getattr(_stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
        getattr(_stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    }
)

_handles: dict[int, str] = {}
_counter = itertools.count(_HANDLE_BASE)


def reduced_active() -> bool:
    """True only on native Windows with the explicit operator opt-in."""

    return _os.name == "nt" and _os.environ.get(ENV_FLAG) == "1"


def _is_surrogate(value: _os.stat_result) -> bool:
    return (
        _stat.S_ISLNK(value.st_mode)
        or getattr(value, "st_reparse_tag", 0) in _REPARSE_TAGS
    )


def _is_handle(value: Any) -> bool:
    return isinstance(value, int) and value in _handles


def _resolve(path: Any, dir_fd: int | None) -> str:
    if _is_handle(path):
        return _handles[path]
    text = _os.fspath(path)
    if dir_fd is None:
        return text
    if dir_fd not in _handles:
        raise OSError(errno.EBADF, f"unknown directory handle: {dir_fd}")
    if _os.path.isabs(text) or _os.path.splitdrive(text)[0]:
        raise OSError(errno.EINVAL, f"absolute path with directory handle: {text}")
    return _os.path.join(_handles[dir_fd], text)


def _register(path: str) -> int:
    handle = next(_counter)
    _handles[handle] = path
    return handle


def _open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
    target = _resolve(path, dir_fd)
    real_flags = flags & ~_VIRTUAL_FLAGS
    if flags & _O_DIRECTORY:
        value = _os.lstat(target)
        if _is_surrogate(value):
            raise OSError(errno.ELOOP, f"path is a symlink or junction: {target}")
        if not _stat.S_ISDIR(value.st_mode):
            raise NotADirectoryError(errno.ENOTDIR, f"not a directory: {target}")
        return _register(target)
    if flags & _O_NOFOLLOW:
        try:
            value = _os.lstat(target)
        except FileNotFoundError:
            value = None
        if value is not None and _is_surrogate(value):
            raise OSError(errno.ELOOP, f"path is a symlink or junction: {target}")
    return _os.open(target, real_flags | getattr(_os, "O_BINARY", 0), mode)


def _close(fd: int) -> None:
    if _is_handle(fd):
        _handles.pop(fd, None)
        return
    _os.close(fd)


def _dup(fd: int) -> int:
    if _is_handle(fd):
        return _register(_handles[fd])
    return _os.dup(fd)


def _fstat(fd: int) -> _os.stat_result:
    if _is_handle(fd):
        return _os.stat(_handles[fd])
    return _os.fstat(fd)


def _fsync(fd: int) -> None:
    if _is_handle(fd):
        return
    _os.fsync(fd)


def _stat_fn(
    path: Any, *, dir_fd: int | None = None, follow_symlinks: bool = True
) -> _os.stat_result:
    target = _resolve(path, dir_fd)
    return _os.stat(target, follow_symlinks=follow_symlinks)


def _lstat(path: Any, *, dir_fd: int | None = None) -> _os.stat_result:
    return _os.lstat(_resolve(path, dir_fd))


def _mkdir(path: Any, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
    _os.mkdir(_resolve(path, dir_fd), mode)


def _unlink(path: Any, *, dir_fd: int | None = None) -> None:
    _os.unlink(_resolve(path, dir_fd))


def _rmdir(path: Any, *, dir_fd: int | None = None) -> None:
    _os.rmdir(_resolve(path, dir_fd))


def _replace(
    src: Any,
    dst: Any,
    *,
    src_dir_fd: int | None = None,
    dst_dir_fd: int | None = None,
) -> None:
    _os.replace(_resolve(src, src_dir_fd), _resolve(dst, dst_dir_fd))


def _rename(
    src: Any,
    dst: Any,
    *,
    src_dir_fd: int | None = None,
    dst_dir_fd: int | None = None,
) -> None:
    # POSIX rename() overwrites an existing file; Windows rename() refuses.
    source, target = _resolve(src, src_dir_fd), _resolve(dst, dst_dir_fd)
    _os.replace(source, target)
    # A POSIX descriptor follows its inode across a rename; emulate that for
    # virtual handles that denote the renamed directory or anything below it.
    prefix = source + _os.sep
    for handle, path in list(_handles.items()):
        if path == source:
            _handles[handle] = target
        elif path.startswith(prefix):
            _handles[handle] = target + path[len(source):]


def _scandir(path: Any = None):
    if _is_handle(path):
        return _os.scandir(_handles[path])
    return _os.scandir(path) if path is not None else _os.scandir()


def _listdir(path: Any = None) -> list[str]:
    if _is_handle(path):
        return _os.listdir(_handles[path])
    return _os.listdir(path) if path is not None else _os.listdir()


def _fchmod(fd: int, mode: int) -> None:
    if _is_handle(fd) or _os.name == "nt":
        return
    _os.fchmod(fd, mode)


def _kill(pid: int, sig: int) -> None:
    """Probe a process with ``sig == 0`` without ever terminating it."""

    if _os.name != "nt" or sig != 0:
        _os.kill(pid, sig)
        return
    import ctypes

    process_query_limited_information = 0x1000
    error_invalid_parameter = 87
    error_access_denied = 5
    still_active = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        code = ctypes.get_last_error()
        if code == error_invalid_parameter:
            raise ProcessLookupError(errno.ESRCH, "no such process")
        if code == error_access_denied:
            raise PermissionError(errno.EACCES, "access denied")
        raise OSError(code, "cannot probe process")
    try:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(exit_code)):
            if exit_code.value != still_active:
                raise ProcessLookupError(errno.ESRCH, "process has exited")
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


class _OsProxy:
    """Attribute-compatible stand-in for :mod:`os` on native Windows."""

    open = staticmethod(_open)
    close = staticmethod(_close)
    dup = staticmethod(_dup)
    fstat = staticmethod(_fstat)
    fsync = staticmethod(_fsync)
    stat = staticmethod(_stat_fn)
    lstat = staticmethod(_lstat)
    mkdir = staticmethod(_mkdir)
    unlink = staticmethod(_unlink)
    rmdir = staticmethod(_rmdir)
    rename = staticmethod(_rename)
    replace = staticmethod(_rename)
    scandir = staticmethod(_scandir)
    listdir = staticmethod(_listdir)
    fchmod = staticmethod(_fchmod)
    kill = staticmethod(_kill)

    _VIRTUAL = {"O_DIRECTORY": _O_DIRECTORY, "O_NOFOLLOW": _O_NOFOLLOW}

    @property
    def supports_dir_fd(self) -> set:
        if reduced_active():
            return {
                _open,
                _mkdir,
                _stat_fn,
                _unlink,
                _rmdir,
                _rename,
                _scandir,
                _listdir,
            }
        return _os.supports_dir_fd

    @property
    def supports_follow_symlinks(self) -> set:
        if reduced_active():
            return {_stat_fn}
        return _os.supports_follow_symlinks

    def __getattr__(self, name: str) -> Any:
        if name in self._VIRTUAL and reduced_active():
            return self._VIRTUAL[name]
        return getattr(_os, name)


os_proxy = _OsProxy()
