# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 nexB Inc. and others. All rights reserved.
# http://nexb.com and https://github.com/nexB/scancode-toolkit/
# The ScanCode software is licensed under the Apache License version 2.0.
# Data generated with ScanCode require an acknowledgment.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# When you publish or redistribute any data created with ScanCode or any ScanCode
# derivative work, you must accompany this data with the following acknowledgment:
#
#  Generated with ScanCode and provided on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, either express or implied. No content created from
#  ScanCode should be considered or used as legal advice. Consult an Attorney
#  for any legal advice.
#  ScanCode is a free software code scanning tool from nexB Inc. and others.
#  Visit https://github.com/nexB/scancode-toolkit/ for support and download.

import logging
import re
import unicodedata

from text_unidecode import unidecode
from bs4.dammit import UnicodeDammit

"""
A text processing module providing functions to process and prepare text
before indexing or fingerprinting such as:
 - case folding
 - conversion of iso latin and unicode to ascii
 - punctuation stripping
 - line separator stripping and conversion
 """

LOG = logging.getLogger(__name__)


def lines(s):
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
    return [l.strip() for l in s.splitlines() if l.strip()]


def foldcase(text):
    """
    Fold the case of a text to lower case.
    """
    return text.lower()


def nopunc():
    return re.compile(r'[\W_]', re.MULTILINE | re.UNICODE)


def nopunctuation(text):
    u"""
    Replaces any non alphanum symbol (i.e. punctuation) in text with space.
    Preserve the characters offsets by replacing punctuation with spaces.
    Warning: this also drops line endings.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return re.sub(nopunc(), ' ', text)


CR = '\r'
LF = '\n'
CRLF = CR + LF
CRLF_NO_CR = ' ' + LF


def unixlinesep(text, preserve=False):
    """
    Normalize a string to Unix line separators. Preserve character offset by
    replacing with spaces if preserve is True.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return text.replace(CRLF, CRLF_NO_CR if preserve else LF).replace(CR, LF)


def nolinesep(text):
    """
    Removes line separators, replacing them with spaces.
    """
    if not isinstance(text, str):
        text = as_unicode(text)
    return text.replace(CR, ' ').replace(LF, ' ')


def toascii(s, translit=False):
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
        s = as_unicode(s)
    if translit:
        converted = unidecode(s)
    else:
        converted = unicodedata.normalize('NFKD', s)

    converted = converted.replace('[?]', '_')
    converted = converted.encode('ascii', 'ignore')
    return converted.decode('ascii')


def python_safe_name(s):
    """
    Return a name derived from string `s` safe to use as a Python identifier.
    """
    if not isinstance(s, str):
        s = as_unicode(s)
    s = toascii(s)
    s = foldcase(s)
    s = nopunctuation(s)
    s = s.replace(' ', '_')
    s = '_'.join(s.split())
    s = s.strip('_')
    return s


def as_unicode(s):
    """
    Return a unicode string for a string be it bytes or unicode.
    """
    if isinstance(s, str):
        return s
    if s == b'':
        return u''
    if not s:
        return s
    assert isinstance(s, bytes), 's must be bytes but is: {}'.format(s)
    return UnicodeDammit(s).markup
