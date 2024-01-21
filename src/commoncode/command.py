#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import contextlib
import ctypes
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from commoncode import text
from commoncode.fileutils import get_temp_dir
from commoncode.system import on_posix, on_windows

"""
Wrapper for executing external commands in sub-processes which works
consistently the same way on POSIX and Windows OSes and can cope with the
capture of large command standard outputs without exhausting memory.
"""

logger = logging.getLogger(__name__)

TRACE = False

if TRACE:
    import sys

    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


PATH_ENV_VAR = "PATH"
LD_LIBRARY_PATH = "LD_LIBRARY_PATH"
DYLD_LIBRARY_PATH = "DYLD_LIBRARY_PATH"


def execute(
    cmd_loc: Path,
    args: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    to_files: bool = False,
    log: bool = TRACE,
) -> tuple[int | Any, Path, Path]:
    """
    Run a `cmd_loc` command with the `args` arguments list and return the return
    code, the stdout and stderr.

    To avoid RAM exhaustion, always write stdout and stderr streams to files.

    If `to_files` is False, return the content of stderr and stdout as ASCII
    strings. Otherwise, return the locations to the stderr and stdout temporary
    files.

    Run the command using the `cwd` current working directory with an `env` dict
    of environment variables.
    """
    assert cmd_loc
    full_cmd = [cmd_loc] + (args or [])

    # any shared object should be either in the PATH, the rpath or
    # side-by-side with the exceutable
    cmd_dir = cmd_loc.parent
    env = get_env(env, lib_dir=cmd_dir) or None
    cwd = cwd or Path.cwd()

    # temp files for stderr and stdout
    tmp_dir: Path = Path(get_temp_dir(prefix="cmd-"))

    sop: Path = tmp_dir / "stdout"
    sep: Path = tmp_dir / "stderr"

    # shell==True is DANGEROUS but we are not running arbitrary commands
    # though we can execute commands that just happen to be in the path
    # See why we need it on Windows https://bugs.python.org/issue8557
    shell = bool(on_windows)

    if log and TRACE:
        logger.debug(
            "Executing command {cmd_loc!r} as:\n{full_cmd!r}\nwith: env={env!r}\n"
            "shell={shell!r}\ncwd={cwd!r}\nstdout={sop!r}\nstderr={sep!r}".format(**locals()),
        )

    proc = None
    rc = 100

    try:
        with sop.open("wb") as stdout, sep.open("wb") as stderr, pushd(cmd_dir):
            proc = subprocess.Popen(
                full_cmd,
                cwd=cwd,
                env=env,
                stdout=stdout,
                stderr=stderr,
                shell=shell,  # noqa: S603
                # -1 defaults bufsize to system bufsize
                bufsize=-1,
                universal_newlines=True,
            )
            stdout, stderr = proc.communicate()
            rc = proc.returncode if proc else 0
    except OSError as e:
        print(e.strerror)

    if not to_files:
        # return output as ASCII string loaded from the output files
        with sop.open("rb") as so:
            sor = so.read()
            sop = Path(text.toascii(sor).strip())

        with sop.open("rb") as se:
            ser = se.read()
            sep = Path(text.toascii(ser).strip())

    return rc, sop, sep


def get_env(base_vars: dict[str, str] | None = None, lib_dir: Path | None = None) -> dict[str, str]:
    """
    Return a dictionary of environment variables for command execution with
    appropriate DY/LD_LIBRARY_PATH path variables. Use the optional `base_vars`
    environment variables dictionary as a base if provided. Note: if `base_vars`
    contains DY/LD_LIBRARY_PATH variables these will be overwritten. On POSIX,
    add `lib_dir` as DY/LD_LIBRARY_PATH-like path if provided.
    """
    env_vars: dict[str, str] = {}
    if base_vars:
        env_vars.update(base_vars)

    # Create and add LD environment variables
    if lib_dir and on_posix:
        new_path = f"{lib_dir}"
        # on Linux/posix
        ld_lib_path = os.environ.get(LD_LIBRARY_PATH)
        env_vars.update({LD_LIBRARY_PATH: update_path_var(ld_lib_path, new_path)})
        # on Mac, though LD_LIBRARY_PATH should work too
        dyld_lib_path = os.environ.get(DYLD_LIBRARY_PATH)
        env_vars.update({DYLD_LIBRARY_PATH: update_path_var(dyld_lib_path, new_path)})

    env_vars = {text.as_unicode(k): text.as_unicode(v) for k, v in env_vars.items()}

    return env_vars


def close(proc: subprocess.Popen) -> None:
    """
    Close a `proc` process opened pipes and kill the process.
    """
    if not proc:
        return

    def close_pipe(p: Any | None) -> None:
        if not p:
            return
        try:
            p.close()
        except OSError:
            pass

    close_pipe(getattr(proc, "stdin", None))
    close_pipe(getattr(proc, "stdout", None))
    close_pipe(getattr(proc, "stderr", None))

    try:
        # Ensure process death otherwise proc.wait may hang in some cases
        # NB: this will run only on POSIX OSes supporting signals
        os.kill(proc.pid, signal.SIGKILL)  # NOQA
    except Exception as e:
        logger.error(e.args)

    # This may slow things down a tad on non-POSIX Oses but is safe:
    # this calls os.waitpid() to make sure the process is dead
    proc.wait()


def load_shared_library(dll_loc: Path | None = None, *args: Any) -> ctypes.CDLL | None:
    """
    Return the loaded shared library object from the ``dll_loc`` location.
    """
    if not dll_loc or not dll_loc.exists():
        raise ImportError(f"Shared library does not exists: dll_loc: {dll_loc}")

    lib = None

    dll_dir = dll_loc.parent
    try:
        with pushd(dll_dir):
            lib = ctypes.CDLL(name=dll_loc.as_posix())
    except OSError as e:
        import traceback
        from pprint import pformat

        msgs = (
            f'ctypes.CDLL("{dll_loc}")',
            f"os.environ:\n{pformat(dict(os.environ))}",
            traceback.format_exc(),
        )
        raise Exception(msgs) from e

    if lib and lib._name:
        return lib

    raise Exception(f"Failed to load shared library with ctypes: {dll_loc}")


@contextlib.contextmanager
def pushd(path: Path | None = None) -> None:
    """
    Context manager to change the current working directory to `path`.
    """
    original_cwd: Path = Path.cwd()
    if not path:
        path = original_cwd
    try:
        os.chdir(path)
        yield Path.cwd()
    finally:
        os.chdir(original_cwd)


def update_path_var(existing_path_var: str | None, new_path: str | None = None) -> str:
    """
    Return an updated value for the `existing_path_var` PATH-like environment
    variable value  by adding `new_path` to the front of that variable if
    `new_path` is not already part of this PATH-like variable.
    """
    if not new_path:
        return existing_path_var if existing_path_var else ""

    existing_path_var = existing_path_var or ""

    existing_path_var = os.fsdecode(existing_path_var)
    new_path = os.fsdecode(new_path)

    path_elements = existing_path_var.split(os.pathsep)

    if not path_elements:
        updated_path_var = new_path

    elif new_path not in path_elements:
        # add new path to the front of the PATH env var
        path_elements.insert(0, new_path)
        updated_path_var = os.pathsep.join(path_elements)

    else:
        # new path is already in PATH, change nothing
        updated_path_var = existing_path_var

    if not isinstance(updated_path_var, str):
        updated_path_var = os.fsdecode(updated_path_var)

    return updated_path_var


PATH_VARS = (
    DYLD_LIBRARY_PATH,
    LD_LIBRARY_PATH,
    "PATH",
)


def find_in_path(filename: str, searchable_paths: Any = searchable_paths()) -> Path | None:
    """
    Return the location of a ``filename`` found in the ``searchable_paths`` list
    of directory or None.
    """
    for path in searchable_paths:
        location: Path = path / filename
        if location.exists():
            return location

    return None
