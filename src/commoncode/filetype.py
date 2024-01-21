#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from commoncode.functional import memoize
from commoncode.system import on_posix

"""
Low level file type utilities, essentially a wrapper around os.path and stat.
"""


def is_regular(location: Path) -> bool:
    """
    Return True if `location` is regular. A regular location is a file or a
    dir and not a special file or symlink.
    """
    return location.exists() and (location.is_file() or location.is_dir())


def is_special(location: Path) -> bool:
    """
    Return True if `location` is a special file . A special file is not a
    regular file, i.e. anything such as a broken link, block file, fifo,
    socket, character device or else.
    """
    return not is_regular(location)


def get_link_target(location: Path) -> Path | None:
    """
    Return the link target for `location` if this is a Link or an empty
    string.
    """
    target: Path | None = None
    # always false on windows, until Python supports junctions/links
    if on_posix and location.is_symlink():
        try:
            # return false on OSes not supporting links
            target = location.readlink()
        except UnicodeEncodeError:
            # location is unicode but readlink can fail in some cases
            pass
    return target


def get_type(location: Path, short: bool = True) -> str | None:
    """
    Return the type of the `location` or None if it does not exist.
    Return the short form (single character) or long form if short=False
    """
    if location.exists():
        mode = location.stat().st_mode
        if location.is_symlink():
            return short and "l" or "link"
        elif location.is_file():
            return short and "f" or "file"
        elif location.is_dir():
            return short and "d" or "directory"
        elif stat.S_ISFIFO(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISSOCK(mode):
            return short and "s" or "special"

    return None


def is_readable(location: Path) -> int | None:
    """
    Return True if the file at location has readable permission set.
    Does not follow links.
    """
    if location.exists():
        mode = location.stat().st_mode
        return (location.is_dir() and mode & os.R_OK and mode & os.X_OK) or (location.is_file() and mode & os.R_OK)

    return None


def is_writable(location: Path) -> bool:
    """
    Return True if the file at location has writeable permission set.
    Does not follow links.
    """
    if location.exists():
        if location.is_dir():
            return os.access(location, os.R_OK | os.W_OK | os.X_OK)
        else:
            return os.access(location, os.R_OK | os.W_OK)

    return False


def is_executable(location: Path) -> bool:
    """
    Return True if the file at location has executable permission set.
    Does not follow links.
    """
    if location.exists():
        if location.is_dir():
            return os.access(location, os.R_OK | os.W_OK | os.X_OK)
        else:
            return os.access(location, os.X_OK)

    return False


def is_rwx(location: Path) -> int | None:
    """
    Return True if the file at location has read, write and executable
    permission set. Does not follow links.
    """
    return is_readable(location) and is_writable(location) and is_executable(location)


def get_last_modified_date(location: Path) -> str:
    """
    Return the last modified date stamp of a file as YYYYMMDD format. The date
    of non-files (dir, links, special) is always an empty string.
    """
    yyyymmdd = ""
    if location.is_file():
        utc_date = datetime.isoformat(
            datetime.utcfromtimestamp(location.stat().st_mtime),
        )
        yyyymmdd = utc_date[:10]
    return yyyymmdd


counting_functions = {
    "file_count": lambda _: 1,
    "file_size": os.path.getsize,
}


@memoize
def counter(location: Path, counting_function: str) -> int:
    """
    Return a count for a single file or a cumulative count for a directory
    tree at `location`.

    Get a callable from the counting_functions registry using the
    `counting_function` string. Call this callable with a `location` argument
    to determine the count value for a single file. This allow memoization
    with hashable arguments.

    Only regular files and directories have a count. The count for a directory
    is the recursive count sum of the directory file and directory
    descendants.

    Any other file type such as a special file or link has a zero size. Does
    not follow links.
    """
    if not location.exists():
        return 0

    if not location.is_file() or location.is_dir():
        return 0

    count: int = 0
    if location.is_file():
        count_fun = counting_functions[counting_function]
        return count_fun(location)
    elif location.is_dir():
        count += sum(counter((location / p).as_posix(), counting_function) for p in location.iterdir())
    return count


def get_file_count(location: Path) -> int:
    """
    Return the cumulative number of files in the directory tree at `location`
    or 1 if `location` is a file. Only regular files are counted. Everything
    else has a zero size.
    """
    return counter(location, "file_count")


def get_size(location: Path) -> int:
    """
    Return the size in bytes of a file at `location` or if `location` is a
    directory, the cumulative size of all files in this directory tree. Only
    regular files have a size. Everything else has a zero size.
    """
    return counter(location, "file_size")
