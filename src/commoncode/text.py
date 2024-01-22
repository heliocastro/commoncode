#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import logging
import re
import unicodedata

from bs4.dammit import UnicodeDammit
from text_unidecode import unidecode

"""
A text processing module providing functions to process and prepare text
before indexing or fingerprinting such as:
 - case folding
 - conversion of iso latin and unicode to ascii
 - punctuation stripping
 - line separator stripping and conversion
 """

LOG = logging.getLogger(__name__)


def lines(s: str) -> list[str]:
    """
    Split a string in lines using the following conventions:
    - a line ending \r\n or \n is a separator and yields a new list element
    - empty lines or lines with only white spaces are not returned.
    - returned lines are stripped.

    Because of these constraints "".split() cannot be used directly. We first
    replace things where we want to split with line endings, then we
    splitlines.
    """
    # FIXME: leverage new Pythin 3.8 scopeing rules
    return [line.strip() for line in s.splitlines() if line.strip()]


def foldcase(text: str) -> str:
    """
    Fold the case of a text to lower case.
    """
    return text.lower()


def nopunc() -> re.Pattern:
    return re.compile(r"[\W_]", re.MULTILINE | re.UNICODE)


def nopunctuation(text: str) -> str:
    """
    Replaces any non alphanum symbol (i.e. punctuation) in text with space.
    Preserve the characters offsets by replacing punctuation with spaces.
    Warning: this also drops line endings.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return re.sub(nopunc(), " ", text)


CR = "\r"
LF = "\n"
CRLF = CR + LF
CRLF_NO_CR = " " + LF


def unixlinesep(text: str, preserve: bool = False) -> str:
    """
    Normalize a string to Unix line separators. Preserve character offset by
    replacing with spaces if preserve is True.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return text.replace(CRLF, CRLF_NO_CR if preserve else LF).replace(CR, LF)


def nolinesep(text: str) -> str:
    """
    Removes line separators, replacing them with spaces.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return text.replace(CR, " ").replace(LF, " ")


def toascii(s: bytes | str, translit: bool = False) -> str:
    """
    Convert a Unicode or byte string to ASCII characters, including replacing
    accented characters with their non-accented equivalent.

    If `translit` is False use the Unicode NFKD equivalence.
    If `translit` is True, use a transliteration with the unidecode library.

    Non ISO-Latin and non ASCII characters are stripped from the output. When no
    transliteration is possible, the resulting character is replaced by an
    underscore "_".

    For Unicode NFKD equivalence, see http://en.wikipedia.org/wiki/Unicode_equivalence
    The convertion may NOT preserve the original string length and with NFKD some
    characters may be deleted.
    Inspired from: http://code.activestate.com/recipes/251871/#c10 by Aaron Bentley.
    """
    if not isinstance(s, str):
        s_unicode = as_unicode(s)
    converted = unidecode(s_unicode) if translit else unicodedata.normalize("NFKD", s_unicode)

    converted = converted.replace("[?]", "_")
    converted = converted.encode("ascii", "ignore")
    return converted.decode("ascii")


def python_safe_name(s: str) -> str:
    """
    Return a name derived from string `s` safe to use as a Python identifier.
    """
    if not isinstance(s, str):
        s = as_unicode(s)
    s = toascii(s)
    s = foldcase(s)
    s = nopunctuation(s)
    s = s.replace(" ", "_")
    s = "_".join(s.split())
    s = s.strip("_")
    return s


def as_unicode(s: bytes | str) -> str:
    """
    Return a unicode string for a string be it bytes or unicode.
    """
    if not s:
        return ""
    elif isinstance(s, str):
        return s
    elif s == b"":
        return ""
    if not isinstance(s, bytes):
        print(f"s must be bytes but is: {s}")
    return UnicodeDammit(s).markup
