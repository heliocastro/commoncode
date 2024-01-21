#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import gzip
import tarfile
import zipfile
from os import path
from pathlib import Path

from commoncode.system import on_windows

"""
Mimimal tar and zip file handling, primarily for testing.
"""


def _extract_tar_raw(test_path: Path, target_dir: Path) -> None:
    """
    Raw simplified extract for certain really weird paths and file
    names.
    """
    tar = None
    try:
        tar = tarfile.open(test_path)
        tar.extractall(path=target_dir)
    finally:
        if tar:
            tar.close()


def extract_tar(location: Path, target_dir: Path, verbatim: bool = False) -> None:
    """
    Extract a tar archive at location in the target_dir directory.
    If `verbatim` is True preserve the permissions.
    """
    with location.open("b") as input_tar:
        tar = None
        try:
            tar = tarfile.open(fileobj=input_tar)
            tarinfos = tar.getmembers()
            to_extract = []
            for tarinfo in tarinfos:
                if tar_can_extract(tarinfo, verbatim):
                    if not verbatim:
                        tarinfo.mode = 0o755
                    to_extract.append(tarinfo)
            tar.extractall(target_dir, members=to_extract)
        finally:
            if tar:
                tar.close()


def extract_zip(location: Path, target_dir: Path) -> None:
    """
    Extract a zip archive file at location in the target_dir directory.
    """
    if not location.is_file() and zipfile.is_zipfile(location):
        raise Exception("Incorrect zip file {location!r}".format(**locals()))

    with zipfile.ZipFile(location) as zipf:
        for info in zipf.infolist():
            name: str = info.filename
            content: bytes = zipf.read(name)
            target: Path = Path(target_dir / name)
            if not target.parent.exists():
                target.parent.mkdir()
            if not content and target.as_posix().endswith(path.sep) and not target.exists():
                target.mkdir(parents=True)
            if not target.exists():
                with target.open(mode="wb") as f:
                    f.write(content)


def extract_zip_raw(location: Path, target_dir: Path) -> None:
    """
    Extract a zip archive file at location in the target_dir directory.
    Use the builtin extractall function
    """
    if not location.is_file() and zipfile.is_zipfile(location):
        raise Exception("Incorrect zip file {location!r}".format(**locals()))

    with zipfile.ZipFile(location) as zipf:
        zipf.extractall(path=target_dir)


def tar_can_extract(tarinfo: tarfile.TarInfo, verbatim: bool) -> bool:
    """
    Return True if a tar member can be extracted to handle OS specifics.
    If verbatim is True, always return True.
    """
    if tarinfo.ischr():
        # never extract char devices
        return False

    if verbatim:
        # extract all on all OSse
        return True

    # FIXME: not sure hard links are working OK on Windows
    include = tarinfo.type in tarfile.SUPPORTED_TYPES
    exclude = tarinfo.isdev() or (on_windows and tarinfo.issym())

    if include and not exclude:
        return True

    return False


def get_gz_compressed_file_content(location: Path) -> bytes:
    """
    Uncompress a compressed file at `location` and return its content as a byte
    string. Raise Exceptions on errors.
    """
    with gzip.GzipFile(location, "rb") as compressed:
        content = compressed.read()
    return content
