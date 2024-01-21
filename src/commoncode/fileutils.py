#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0 AND Python-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import errno
import ntpath
import os
import posixpath
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from scancode_config import scancode_temp_dir  # type: ignore
except ImportError:
    scancode_temp_dir = None

from commoncode import filetype

# this exception is not available on posix
try:
    WindowsError  # type: ignore
except NameError:

    class WindowsError(Exception):
        winerror: int


import logging

logger = logging.getLogger(__name__)

TRACE = False


def logger_debug(*args: Any) -> None:
    pass


if TRACE:
    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)

    def logger_debug(*args: Any) -> None:
        logger.debug(" ".join(isinstance(a, str) and a or repr(a) for a in args))


"""
File, paths and directory utility functions.
"""

#
# DIRECTORIES
#


def chmod_recursive(path: Path, mode: int) -> None:
    for child in path.iterdir():
        if child.is_file():
            child.chmod(mode)
        else:  # if the child is a directory
            chmod_recursive(child, mode)
    path.chmod(mode)  # change the directory's permissions after changing its contents


# usage
chmod_recursive(Path("/path/to/directory"), 0o755)


def create_dir(location: Path) -> None:
    """
    Create directory and all sub-directories recursively at location ensuring these
    are readable and writeable.
    Raise Exceptions if it fails to create the directory.
    """

    if location.exists():
        if not location.is_dir():
            err = f"Cannot create directory: existing file in the way {location.as_posix()}s."
            raise OSError(err % locals())
    else:
        # may fail on win if the path is too long
        # FIXME: consider using UNC ?\\ paths

        try:
            location.mkdir(parents=True)
            chmod_recursive(location, RW)

        # avoid multi-process TOCTOU conditions when creating dirs
        # the directory may have been created since the exist check
        except WindowsError as e:
            # [Error 183] Cannot create a file when that file already exists
            if e and e.winerror == 183:
                if not location.is_dir():
                    raise
            else:
                raise
        except OSError as o:
            if o.errno == errno.EEXIST:
                if not location.is_dir():
                    raise
            else:
                raise


def get_temp_dir(base_dir: Path | None = None, prefix: str | None = None) -> Path:
    """
    Return the path to a new existing unique temporary directory, created under
    the `base_dir` base directory using the `prefix` prefix.
    If `base_dir` is not provided, use the 'SCANCODE_TMP' env var or the system
    temp directory.

    WARNING: do not change this code without changing scancode_config.py too
    """

    if scancode_temp_dir:
        base_dir = Path(scancode_temp_dir)

    has_base = bool(base_dir)
    if not has_base:
        scancode_tmp = os.getenv("SCANCODE_TMP")
        if scancode_tmp:  # noqa: SIM108
            base_dir = Path(scancode_tmp)
        else:
            base_dir = Path(tempfile.gettempdir())

    if base_dir:
        Path(base_dir).mkdir(parents=True)

        if not has_base:
            prefix = "scancode-tk-"

    return Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))


#
# PATHS AND NAMES MANIPULATIONS
#

# TODO: move these functions to paths.py


def is_posixpath(location: Path) -> bool:
    """
    Return True if the `location` path is likely a POSIX-like path using POSIX path
    separators (slash or "/")or has no path separator.

    Return False if the `location` path is likely a Windows-like path using backslash
    as path separators (e.g. "\").
    """
    return str(location) == location.as_posix()


def split_parent_resource(path: Path, force_posix: bool = False) -> tuple[str, str]:
    """
    Return a tuple of (parent directory path, resource name).
    """
    use_posix = force_posix or is_posixpath(path)
    splitter = use_posix and posixpath or ntpath
    return splitter.split(path.as_posix())


#
# DIRECTORY AND FILES WALKING/ITERATION
#


def ignore_nothing(_: Any) -> bool:
    return False


def walk(location: Path, ignored: Any | None = None, follow_symlinks: bool = False) -> Any:
    """
    Walk location returning the same tuples as os.walk but with a different
    behavior:
     - always walk top-down, breadth-first.
     - ignore and do not follow symlinks unless `follow_symlinks` is True,
     - always ignore special files (FIFOs, etc.)
     - optionally ignore files and directories by invoking the `ignored`
       callable on files and directories returning True if it should be ignored.
     - location is a directory or a file: for a file, the file is returned.

    If `follow_symlinks` is True, then symlinks will not be ignored and be
    collected like regular files and directories
    """
    # TODO: consider using the new "scandir" module for some speed-up.

    is_ignored = ignored(location) if ignored else False
    if is_ignored:
        if TRACE:
            logger_debug("walk: ignored:", location.as_posix(), is_ignored)
        return

    if filetype.is_file(location, follow_symlinks=follow_symlinks):
        yield location.parent, [], [location.name]

    elif location.is_dir():
        dirs = []
        files = []
        for loc in location.iterdir():
            if filetype.is_special(loc) or (ignored and ignored(loc)):
                if follow_symlinks and loc.is_symlink() and not location.exists():
                    pass
                else:
                    if TRACE:
                        ign = ignored and ignored(loc)
                        logger_debug("walk: ignored:", loc, ign)
                    continue
            # special files and symlinks are always ignored
            if filetype.is_dir(loc, follow_symlinks=follow_symlinks):
                dirs.append(loc.name)
            elif filetype.is_file(loc, follow_symlinks=follow_symlinks):
                files.append(loc.name)
        yield location, dirs, files

        for dr in dirs:
            yield from walk(Path(location / dr), ignored, follow_symlinks=follow_symlinks)


def resource_iter(
    location: Path,
    ignored: Any | bool = ignore_nothing,
    with_dirs: bool = True,
    follow_symlinks: bool = False,
) -> Path:
    """
    Return an iterable of paths at `location` recursively.

    :param location: a file or a directory.
    :param ignored: a callable accepting a location argument and returning True
                    if the location should be ignored.
    :return: an iterable of file and directory locations.
    """
    for top, dirs, files in walk(location, ignored, follow_symlinks=follow_symlinks):
        if with_dirs:
            for d in dirs:
                yield Path(top / d)
        for f in files:
            yield Path(top / f)


#
# COPY
#


def copytree(src: Path, dst: Path) -> None:
    """
    Copy recursively the `src` directory to the `dst` directory. If `dst` is an
    existing directory, files in `dst` may be overwritten during the copy.
    Preserve timestamps.
    Ignores:
     -`src` permissions: `dst` files are created with the default permissions.
     - all special files such as FIFO or character devices and symlinks.

    Raise an shutil.Error with a list of reasons.

    This function is similar to and derived from the Python shutil.copytree
    function. See fileutils.py.ABOUT for details.
    """

    if not filetype.is_readable(src):
        src.chmod(mode=R)

    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=False)

    errors = []
    errors.extend(copytime(src, dst))

    for srcname in src.iterdir():
        dstname: Path = dst / srcname.name

        # skip anything that is not a regular file, dir or link
        if not filetype.is_regular(srcname.as_posix()):
            continue

        if not filetype.is_readable(srcname.as_posix()):
            srcname.chmod(R)
        try:
            if srcname.is_dir():
                copytree(srcname, dstname)
            elif srcname.is_file():
                copyfile(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname.as_posix(), dstname.as_posix(), str(why)))

    if errors:
        raise shutil.Error(errors)


def copyfile(src: Path, dst: Path) -> None:
    """
    Copy src file to dst file preserving timestamps.
    Ignore permissions and special files.

    Similar to and derived from Python shutil module. See fileutils.py.ABOUT
    for details.
    """
    if not filetype.is_regular(src):
        return
    if not filetype.is_readable(src):
        src.chmod(R)
    if dst.is_dir():
        dst = dst / src.name
    shutil.copyfile(src, dst)
    copytime(src, dst)


def copytime(src: Path, dst: Path) -> list[tuple[str, str, str]]:
    """
    Copy timestamps from `src` to `dst`.

    Similar to and derived from Python shutil module. See fileutils.py.ABOUT
    for details.
    """
    errors = []
    st = src.stat()
    if hasattr(os, "utime"):
        try:
            os.utime(dst, (st.st_atime, st.st_mtime))
        except OSError as why:
            if WindowsError is not None and isinstance(why, WindowsError):
                # File access times cannot be copied on Windows
                pass
            else:
                errors.append((src.as_posix(), dst.as_posix(), str(why)))
    return errors


#
# PERMISSIONS
#


# modes: read, write, executable
R = stat.S_IRUSR
RW = stat.S_IRUSR | stat.S_IWUSR
RX = stat.S_IRUSR | stat.S_IXUSR
RWX = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

#
# DELETION


def _rm_handler(function: Callable[..., Any], path: str, excinfo: Any) -> None:
    """
    shutil.rmtree handler invoked on error when deleting a directory tree.
    This retries deleting once before giving up.
    """
    if TRACE:
        logger_debug("_rm_handler:", "path:", path, "excinfo:", excinfo)

    _path: Path = Path(path)
    if function in (os.rmdir, os.listdir):
        try:
            _path.chmod(RW)
            shutil.rmtree(path, True)
        except Exception:
            logger.warning("Failed to delete directory %s", path)

        if _path.exists():
            logger.warning("Failed to delete directory %s", path)
    elif function == os.remove:
        try:
            _path.unlink()
        except Exception:
            logger.warning("Failed to delete directory %s", path)

        if _path.exists():
            logger.warning("Failed to delete file %s", path)
