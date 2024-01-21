#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from collections import defaultdict
from filecmp import dircmp
from itertools import chain
from pathlib import Path
from typing import Any
from unittest import TestCase as TestCaseClass

import saneyaml

from commoncode import fileutils
from commoncode.archive import (
    extract_tar,
    extract_zip,
    extract_zip_raw,
)
from commoncode.system import on_posix

# set to 1 to see the slow tests
timing_threshold = sys.maxsize


def get_test_loc(
    test_path: Path | None,
    test_data_dir: Path | None,
    debug: bool = False,
    must_exist: bool = True,
) -> Path:
    """
    Given a `test_path` relative to the `test_data_dir` directory, return the
    location to a test file or directory for this path. No copy is done.
    Raise an IOError if `must_exist` is True and the `test_path` does not exists.
    """
    if debug:
        import inspect

        caller = inspect.stack()[1][3]
        print('\nget_test_loc,{caller},"{test_path}","{test_data_dir}"'.format(**locals()))

    if not test_path or not test_data_dir:
        raise ValueError

    if not test_data_dir.exists():
        raise OSError("[Errno 2] No such directory: test_data_dir not found:" " '{test_data_dir}'".format(**locals()))

    test_loc: Path = test_data_dir / test_path

    if must_exist and not test_loc.exists():
        raise OSError("[Errno 2] No such file or directory: " "test_path not found: '{test_loc}'".format(**locals()))

    return test_loc


class FileDrivenTesting:
    """
    Add support for handling test files and directories, including managing
    temporary test resources and doing file-based assertions.
    This can be used as a standalone object if needed.
    """

    test_data_dir: Path | None = None

    def get_test_loc(self, test_path: Path, copy: bool = False, debug: bool = False, must_exist: bool = True) -> Path:
        """
        Given a `test_path` relative to the self.test_data_dir directory, return the
        location to a test file or directory for this path. Copy to a temp
        test location if `copy` is True.

        Raise an IOError if `must_exist` is True and the `test_path` does not
        exists.
        """
        if debug:
            import inspect

            caller = inspect.stack()[1][3]
            print('\nself.get_test_loc,{caller},"{test_path}"'.format(**locals()))

        test_loc = get_test_loc(
            test_path,
            self.test_data_dir,
            debug=debug,
            must_exist=must_exist,
        )
        if copy:
            base_name = test_loc.name
            if test_loc.is_file():
                # target must be an existing dir
                target_dir = self.get_temp_dir()
                fileutils.copyfile(test_loc, target_dir)
                test_loc = target_dir / base_name
            else:
                # target must be a NON existing dir
                target_dir = self.get_temp_dir() / base_name
                fileutils.copytree(test_loc, target_dir)
                # cleanup of VCS that could be left over from checkouts
                self.remove_vcs(target_dir)
                test_loc = target_dir
        return test_loc

    def get_temp_file(self, extension: str | None = None, dir_name: str = "td", file_name: str = "tf") -> Path:
        """
        Return a unique new temporary file location to a non-existing temporary
        file that can safely be created without a risk of name collision.
        """
        if extension is None:
            extension = ".txt"

        if extension and not extension.startswith("."):
            extension = "." + extension

        file_name = file_name + extension
        location: Path = self.get_temp_dir(dir_name) / file_name
        return location

    def get_temp_dir(self, sub_dir_path: str | None = None) -> Path:
        """
        Create a unique new temporary directory location. Create directories
        identified by sub_dir_path if provided in this temporary directory.
        Return the location for this unique directory joined with the
        `sub_dir_path` if any.
        """

        # ensure that we have a new unique temp directory for each test run
        import tempfile

        self.test_run_temp_dir: Path | None = fileutils.get_temp_dir(base_dir=Path(tempfile.gettempdir()), prefix="")

        if sub_dir_path:
            # create a sub directory hierarchy if requested
            self.test_run_temp_subdir: Path = (
                fileutils.get_temp_dir(base_dir=self.test_run_temp_dir, prefix="") / sub_dir_path
            )
            self.test_run_temp_subdir.mkdir(parents=True)
        return self.test_run_temp_subdir

    def remove_vcs(self, test_dir: Path) -> None:
        """
        Remove some version control directories and some temp editor files.
        """
        vcses = ("CVS", ".svn", ".git", ".hg")
        for root, dirs, files in os.walk(test_dir):
            for vcs_dir in vcses:
                if vcs_dir in dirs:
                    for vcsroot, vcsdirs, vcsfiles in os.walk(test_dir):
                        for vcsfile in vcsdirs + vcsfiles:
                            vfile: Path = Path(vcsroot) / vcsfile
                            vfile.chmod(fileutils.RW)
                    shutil.rmtree(Path(root) / vcs_dir, False)

            # editors temp file leftovers
            tilde_files = [Path(root) / file_loc for file_loc in files if file_loc.endswith("~")]
            for tf in tilde_files:
                tf.unlink()

    def __extract(self, test_path: Path | None, extract_func: Any | None = None, verbatim: bool = False) -> Path:
        """
        Given an archive file identified by test_path relative
        to a test files directory, return a new temp directory where the
        archive file has been extracted using extract_func.
        If `verbatim` is True preserve the permissions.
        """
        assert test_path and test_path != ""
        target_path = test_path.name
        target_dir = self.get_temp_dir(target_path)
        original_archive = self.get_test_loc(test_path)
        if extract_func:
            extract_func(original_archive, target_dir, verbatim=verbatim)
        return target_dir

    def extract_test_zip(self, test_path: Path, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Path:
        return self.__extract(test_path, extract_zip)

    def extract_test_zip_raw(self, test_path: Path, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Path:
        return self.__extract(test_path, extract_zip_raw)

    def extract_test_tar(
        self,
        test_path: Path,
        verbatim: bool = False,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Path:
        return self.__extract(test_path, extract_tar, verbatim)

    # def extract_test_tar_raw(self, test_path: Path, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Path:
    #     return self.__extract(test_path, extract_tar_raw)

    # def extract_test_tar_unicode(self, test_path: Path, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Path:
    #     return self.__extract(test_path, extract_tar_uni)


class FileBasedTesting(TestCaseClass, FileDrivenTesting):
    pass


def is_same(dir1: Path, dir2: Path) -> bool:
    """
    Compare two directory trees for structure and file content.
    Return False if they differ, True is they are the same.
    """
    compared = dircmp(dir1, dir2)
    if compared.left_only or compared.right_only or compared.diff_files or compared.funny_files:
        return False

    return all(is_same(dir1 / subdir, dir2 / subdir) for subdir in compared.common_dirs)


def file_cmp(file1: Path, file2: Path, ignore_line_endings: bool = False) -> bool:
    """
    Compare two files content.
    Return False if they differ, True is they are the same.
    """
    with file1.open("rb") as f1:
        f1c = f1.read()
        if ignore_line_endings:
            f1c = b"\n".join(f1c.splitlines(False))
    with file2.open("rb") as f2:
        f2c = f2.read()
        if ignore_line_endings:
            f2c = b"\n".join(f2c.splitlines(False))
    return bool(f2c == f1c)


def make_non_readable(location: Path) -> None:
    """
    Make location non readable for tests purpose.
    """
    if on_posix:
        current_stat = stat.S_IMODE(os.lstat(location).st_mode)
        location.chmod(current_stat & ~stat.S_IREAD)
    else:
        location.chmod(0o555)


def make_non_writable(location: Path) -> None:
    """
    Make location non writable for tests purpose.
    """
    if on_posix:
        current_stat = stat.S_IMODE(os.lstat(location).st_mode)
        location.chmod(current_stat & ~stat.S_IWRITE)
    else:
        make_non_readable(location)


def make_non_executable(location: Path) -> None:
    """
    Make location non executable for tests purpose.
    """
    if on_posix:
        current_stat = stat.S_IMODE(location.lstat().st_mode)
        location.chmod(current_stat & ~stat.S_IEXEC)


def get_test_file_pairs(test_dir: Path) -> tuple[Path, Path]:
    """
    Yield tuples of (data_file, test_file) from a test data `test_dir` directory.
    Raise exception for orphaned/dangling files.
    Each test consist of a pair of files:
    - a test file.
    - a data file with the same name as a test file and a '.yml' extension added.
    Each test file path should be unique in the tree ignoring case.
    """
    # collect files with .yml extension and files with other extensions
    data_files: dict[str, Path] = {}
    test_files: dict[str, Path] = {}
    dangling_test_files = set()
    dangling_data_files = set()
    paths_ignoring_case = defaultdict(list)

    for top, _, files in os.walk(test_dir):
        for tfile in files:
            if tfile.endswith("~"):
                continue
            file_path: Path = Path(top) / tfile

            if tfile.endswith(".yml"):
                data_file_path: Path = file_path
                test_file_path: Path = file_path.with_suffix("")
            else:
                test_file_path = file_path
                data_file_path = test_file_path.with_suffix(".yml")

            if not test_file_path.exists():
                dangling_test_files.add(test_file_path)

            if not data_file_path.exists():
                dangling_data_files.add(data_file_path)

            paths_ignoring_case[file_path.as_posix().lower()].append(file_path)

            data_files[test_file_path.as_posix().lower()] = data_file_path
            test_files[test_file_path.as_posix().lower()] = test_file_path

    # ensure that we haev no dangling files
    if dangling_test_files or dangling_data_files:
        msg = ["Dangling missing test files without a YAML data file:"] + sorted(dangling_test_files)
        msg += ["Dangling missing YAML data files without a test file"] + sorted(dangling_data_files)
        raise Exception(msg)

    # ensure that each data file has a corresponding test file
    diff = set(data_files.keys()).symmetric_difference(set(test_files.keys()))
    if diff:
        msg = [
            "Orphaned copyright test file(s) found: "
            "test file without its YAML test data file "
            "or YAML test data file without its test file.",
        ]
        raise Exception(msg)

    # ensure that test file paths are unique when you ignore case
    # we use the file names as test method names (and we have Windows that's
    # case insensitive
    dupes = list(chain.from_iterable(paths for paths in paths_ignoring_case.values() if len(paths) != 1))
    if dupes:
        msg = ["Non unique test/data file(s) found when ignoring case!"] + sorted(dupes)
        raise Exception(msg)

    for test_file in test_files:
        yield Path(test_file).with_suffix(".yml"), Path(test_file)


def check_against_expected_json_file(results: Any, expected_file: Path, regen: bool = False) -> bool:
    """
    Check that the ``results`` data are the same as the data in the
    ``expected_file`` expected JSON data file.

    If `regen` is True the expected_file will overwritten with the ``results``.
    This is convenient for updating tests expectations. But use with caution.
    """
    if regen:
        with expected_file.open("w") as reg:
            json.dump(results, reg, indent=2, separators=(",", ": "))
        expected = results
    else:
        with expected_file.open("w") as exp:
            expected = json.load(exp)

    # NOTE we redump the JSON as a YAML string for easier display of
    # the failures comparison/diff
    if results != expected:
        expected = saneyaml.dump(expected)
        results = saneyaml.dump(results)
        return bool(results == expected)
    return False
