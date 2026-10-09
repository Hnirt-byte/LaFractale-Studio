"""Linux/POSIX file creation confined to verified directory descriptors.

Untrusted output paths are traversed component-by-component using O_NOFOLLOW.
Only newly created regular files may be opened for writing. This module does
not claim to sandbox malicious Python running with the process's own UID.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat
from typing import Iterator


class UnsafeOutputPath(ValueError):
    """Output path would follow a symlink or replace an unsafe object."""


def _flags() -> int:
    needed = ("O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in needed) or os.open not in os.supports_dir_fd:
        raise UnsafeOutputPath("openat/O_NOFOLLOW obligatoires pour les écritures PDF")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


@contextmanager
def parent_dirfd(path: str | Path, *, create: bool = False) -> Iterator[tuple[int, str]]:
    """Anchor a path's *parent* without resolving or following any symlink.

    Only the leaf basename is returned. Operations on it must use dir_fd.
    """
    raw = os.fspath(path)
    if not raw or "\x00" in raw:
        raise UnsafeOutputPath("Chemin de sortie vide ou invalide")
    raw_parts = Path(raw).parts
    if ".." in raw_parts:
        raise UnsafeOutputPath("Traversée '..' interdite dans un chemin de sortie")
    absolute = Path(os.path.abspath(raw))
    if absolute.name in {"", ".", ".."}:
        raise UnsafeOutputPath("Nom de sortie invalide")
    parts = absolute.parts[1:-1]
    flags = _flags()
    try:
        fd = os.open("/", flags)
    except OSError as exc:
        raise UnsafeOutputPath(f"Impossible d'ouvrir la racine du chemin de sortie : {exc}") from exc
    try:
        for component in parts:
            try:
                try:
                    new_fd = os.open(component, flags, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                    new_fd = os.open(component, flags, dir_fd=fd)
            except OSError as exc:
                # Path traversal errors are classified here, rather than over
                # the yielded caller's body. A render/replace failure must not
                # masquerade as a path-policy failure.
                raise UnsafeOutputPath(
                    f"Parent de sortie absent, non répertoire ou symlink interdit : {exc}"
                ) from exc
            os.close(fd)
            fd = new_fd
        yield fd, absolute.name
    finally:
        os.close(fd)


def validate_leaf_dir(parent_fd: int, name: str) -> bool:
    """Check output leaf without following it. Return whether it exists."""
    try:
        mode = os.stat(name, dir_fd=parent_fd, follow_symlinks=False).st_mode
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(mode):
        raise UnsafeOutputPath("Répertoire de sortie invalide ou symlink interdit")
    return True


@contextmanager
def new_regular_file(path: str | Path) -> Iterator[object]:
    """Create a new PDF exclusively; never overwrite a link or existing file."""
    with parent_dirfd(path, create=True) as (parent_fd, basename):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(basename, flags, 0o600, dir_fd=parent_fd)
        except OSError as exc:
            raise UnsafeOutputPath(f"PDF existant, symlink ou chemin non sûr : {exc}") from exc
        success = False
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise UnsafeOutputPath("Sortie PDF non régulière")
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                yield stream
            success = True
        finally:
            if fd >= 0:
                os.close(fd)
            if not success:
                os.unlink(basename, dir_fd=parent_fd)


@contextmanager
def audit_root_dirfd(path: str | Path) -> Iterator[Path]:
    """Anchor the audited root itself via O_NOFOLLOW (including all parents).

    Yield /proc/self/fd/<root_fd> for all reads during the audit so renaming
    ancestors cannot redirect it to an unverified directory. Linux only,
    matching the existing secure output contract. Never resolve user input.
    """
    with parent_dirfd(path, create=False) as (parent_fd, basename):
        if not validate_leaf_dir(parent_fd, basename):
            raise UnsafeOutputPath("Répertoire racine à auditer inexistant")
        try:
            root_fd = os.open(basename, _flags(), dir_fd=parent_fd)
        except OSError as exc:
            raise UnsafeOutputPath(
                f"Répertoire racine à auditer symlinké/inaccessible : {exc}"
            ) from exc
        try:
            yield Path(f"/proc/self/fd/{root_fd}")
        finally:
            os.close(root_fd)
