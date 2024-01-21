#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import fnmatch
from pathlib import Path

TRACE = False
if TRACE:
    import logging
    import sys

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    logger.setLevel(logging.DEBUG)

"""
Match files and directories paths based on inclusion and exclusion glob-style
patterns.

For example, this can be used to skip files that match ignore patterns,
similar to a version control ignore files such as .gitignore.

The pattern syntax is the same as fnmatch(5) as implemented in Python.

Patterns are applied to a path this way:
 - Paths are converted to POSIX paths before matching.
 - Patterns are NOT case-sensitive.
 - Leading slashes are ignored.
 - If the pattern contains a /, then the whole path must be matched;
   otherwise, the pattern matches if any path segment matches.
 - When matched, a directory content is matched recursively.
   For instance, when using patterns for ignoring, a matched directory will
   be ignored with its file and sub-directories at full depth.
 - The order of patterns does not matter, except for exclusions vs. inclusions.
 - Exclusion patterns are prefixed with an exclamation mark (bang or !)
   meaning that matched paths by that pattern will be excluded. Exclusions
   have precedence of inclusions.
 - Patterns starting with # are comments and skipped. use [#] for a literal #.
 - to match paths relative to some root path, you must design your patterns
   and the paths to be tested accordingly. This module does not handles this.

Patterns may include glob wildcards such as:
 - ? : matches any single character.
 - * : matches 0 or more characters.
 - [seq] : matches any character in seq
 - [!seq] :matches any character not in seq
For a literal match, wrap the meta-characters in brackets. For example, '[?]'
matches the character '?'.
"""


def is_included(path: Path, includes: dict[str, str] | None = None, excludes: dict[str, str] | None = None) -> bool:
    """
    Return a True if `path` is included based on mapping of `includes` and
    `excludes` glob patterns. If the `path` is empty, return False.

    Matching is done based on the set of `includes` and `excludes` patterns maps
    of {fnmatch pattern: message}. If `includes` are provided they are tested
    first. The `excludes` are tested second if provided.

    The ordering of the includes and excludes items does not matter and if a map
    is empty, it is not used for matching.
    """
    if not path.exists():
        return False

    if not includes and not excludes:
        return True

    includes = includes or {}
    includes = {k: v for k, v in includes.items() if k}
    excludes = excludes or {}
    excludes = {k: v for k, v in excludes.items() if k}

    if includes:
        included = get_matches(path, includes, all_matches=False)
        if TRACE:
            logger.debug("in_fileset: path: {path!r} included:{included!r}".format(**locals()))
        if not included:
            return False

    if excludes:
        excluded = get_matches(path, excludes, all_matches=False)
        if TRACE:
            logger.debug("in_fileset: path: {path!r} excluded:{excluded!r} .".format(**locals()))
        if excluded:
            return False

    return True


def get_matches(path: Path, patterns: dict[str, str], all_matches: bool = False) -> str | list[str] | None:
    """
    Return a list of values (which are values from the matched `patterns`
    mappint of {pattern: value or message} if `path` is matched by any of the
    pattern from the `patterns` map or an empty list.
    If `all_matches` is False, stop and return on the first matched pattern.
    """
    if not path.exists():
        return None

    # if TRACE:
    #     logger.debug("_match: path: {path.as_posix()!r} patterns:{patterns!r}.".format(**locals()))

    matches = []
    if not isinstance(patterns, dict):
        assert isinstance(patterns, list | tuple), f"Invalid patterns: {patterns}"
        patterns = {p: p for p in patterns}

    for pat, value in patterns.items():
        if not pat or not pat.strip():
            continue

        value = value or ""
        pat = pat.lstrip("/").lower()
        is_plain = "/" not in pat

        # if is_plain:
        #     if any(fnmatch.fnmatchcase(s, pat) for s in segments):
        #         matches.append(value)
        #         if not all_matches:
        #             break
        if fnmatch.fnmatchcase(path.as_posix(), pat):
            matches.append(value)
            if not all_matches:
                break
    if TRACE:
        logger.debug("_match: matches: {matches!r}".format(**locals()))

    if not all_matches:
        if matches:
            return matches[0]
        else:
            return None
    return matches


def load(location: Path) -> list[str] | None:
    """
    Return a sequence of patterns from a file at location.
    """
    if not location.exists():
        return None

    fn: Path = location.absolute()
    msg = ("File {location} does not exist or not a file.").format(**locals())
    assert fn.exists() and fn.is_file(), msg
    with fn.open() as f:
        return [line.strip() for line in f if line and line.strip()]


def includes_excludes(patterns: list[str], message: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Return a dict of included patterns and a dict of excluded patterns from a
    sequence of `patterns` strings and a `message` setting the message as
    value in the returned mappings. Ignore pattern as comments if prefixed
    with #. Use an empty string is message is None.
    """
    message = message or ""
    bang: str = "!"
    pound: str = "#"
    included: dict[str, str] = {}
    excluded: dict[str, str] = {}
    if not patterns:
        return included, excluded

    for pat in patterns:
        pat = pat.strip()
        if not pat or pat.startswith(pound):
            continue
        if pat.startswith(bang):
            cpat = pat.lstrip(bang)
            if cpat:
                excluded[cpat] = message
            continue
        else:
            included[pat] = message
    return included, excluded
