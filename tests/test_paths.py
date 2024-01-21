#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

from unittest import TestCase

from commoncode import paths


class TestPortablePath(TestCase):
    def test_safe_path_mixed_slashes(self):
        test = paths.safe_path("C:\\Documents and Settings\\Boki\\Desktop\\head\\patches\\drupal6/drupal.js")
        expected = "C/Documents_and_Settings/Boki/Desktop/head/patches/drupal6/drupal.js"
        assert test == expected

    def test_safe_path_mixed_slashes_and_spaces(self):
        test = paths.safe_path("C:\\Documents and Settings\\Boki\\Desktop\\head\\patches\\parallel uploads/drupal.js")
        expected = "C/Documents_and_Settings/Boki/Desktop/head/patches/parallel_uploads/drupal.js"
        assert test == expected

    def test_safe_path_windows_style(self):
        test = paths.safe_path("C:\\Documents and Settings\\Administrator\\Desktop\\siftDemoV4_old\\defs.h")
        expected = "C/Documents_and_Settings/Administrator/Desktop/siftDemoV4_old/defs.h"
        assert test == expected

    def test_safe_path_windows_style_mixed_slashes_no_spaces(self):
        test = paths.safe_path("C:\\Documents and Settings\\Boki\\Desktop\\head\\patches\\imagefield/imagefield.css")
        expected = "C/Documents_and_Settings/Boki/Desktop/head/patches/imagefield/imagefield.css"
        assert test == expected

    def test_safe_path_windows_style_spaces(self):
        test = paths.safe_path("C:\\Documents and Settings\\Boki\\Desktop\\head\\patches\\js delete\\imagefield.css")
        expected = "C/Documents_and_Settings/Boki/Desktop/head/patches/js_delete/imagefield.css"
        assert test == expected

    def test_safe_path_windows_style_posix_slashes(self):
        test = paths.safe_path(
            "C:/Documents and Settings/Alex Burgel/workspace/Hibernate3.2/test/org/hibernate/test/AllTests.java",
        )
        expected = "C/Documents_and_Settings/Alex_Burgel/workspace/Hibernate3.2/test/org/hibernate/test/AllTests.java"
        assert test == expected

    def test_safe_path_windows_style_relative(self):
        test = paths.safe_path("includes\\webform.components.inc")
        expected = "includes/webform.components.inc"
        assert test == expected

    def test_safe_path_windows_style_absolute_trailing_slash(self):
        test = paths.safe_path("\\includes\\webform.components.inc\\")
        expected = "includes/webform.components.inc"
        assert test == expected

    def test_safe_path_posix_style_relative(self):
        test = paths.safe_path("includes/webform.components.inc")
        expected = "includes/webform.components.inc"
        assert test == expected

    def test_safe_path_posix_style_absolute_trailing_slash(self):
        test = paths.safe_path("/includes/webform.components.inc/")
        expected = "includes/webform.components.inc"
        assert test == expected

    def test_safe_path_posix_style_french_char(self):
        test = paths.safe_path("/includes/webform.compon\xc3nts.inc/")
        expected = "includes/webform.componAnts.inc"
        assert test == expected

    def test_safe_path_posix_style_chinese_char(self):
        test = paths.safe_path(b"/includes/webform.compon\xd2\xaants.inc/")
        expected = "includes/webform.componNSnts.inc"
        assert test == expected

    def test_safe_path_windows_style_dots(self):
        test = paths.safe_path("\\includes\\..\\webform.components.inc\\")
        expected = "webform.components.inc"
        assert test == expected

    def test_safe_path_windows_style_many_dots(self):
        test = paths.safe_path(".\\includes\\.\\..\\..\\..\\webform.components.inc\\.")
        expected = "dotdot/dotdot/webform.components.inc"
        assert test == expected

    def test_safe_path_posix_style_dots(self):
        test = paths.safe_path("includes/../webform.components.inc")
        expected = "webform.components.inc"
        assert test == expected

    def test_safe_path_posix_style_many_dots(self):
        test = paths.safe_path("./includes/./../../../../webform.components.inc/.")
        expected = "dotdot/dotdot/dotdot/webform.components.inc"
        assert test == expected

    def test_safe_path_posix_only(self):
        test_path = "var/lib/dpkg/info/libgsm1:amd64.list"
        test = paths.safe_path(test_path)
        expected = "var/lib/dpkg/info/libgsm1_amd64.list"
        assert test == expected
        test = paths.safe_path(test_path, posix_only=True)
        assert test == test_path

    def test_resolve_mixed_slash(self):
        test = paths.resolve("C:\\..\\./drupal.js")
        expected = "C/drupal.js"
        assert test == expected

    def test_resolve_2(self):
        test = paths.resolve("\\includes\\..\\webform.components.inc\\")
        expected = "webform.components.inc"
        assert test == expected

    def test_resolve_3(self):
        test = paths.resolve("includes/../webform.components.inc")
        expected = "webform.components.inc"
        assert test == expected

    def test_resolve_4(self):
        test = paths.resolve("////.//includes/./../..//..///../webform.components.inc/.")
        expected = "dotdot/dotdot/dotdot/webform.components.inc"
        assert test == expected

    def test_resolve_5(self):
        test = paths.resolve("////.//includes/./../..//..///../webform.components.inc/.")
        expected = "dotdot/dotdot/dotdot/webform.components.inc"
        assert test == expected

    def test_resolve_6(self):
        test = paths.resolve("includes/../")
        expected = "."
        assert test == expected

    def test_portable_filename(self):
        expected = "A___file__with_Spaces.mov"
        assert paths.portable_filename("A:\\ file/ with Spaces.mov") == expected

        # Test `preserve_spaces` option. Spaces should not be replaced
        expected = "Program Files (x86)"
        assert paths.portable_filename("Program Files (x86)", preserve_spaces=True) == expected

        # Unresolved relative paths will be treated as a single filename. Use
        # resolve instead if you want to resolve paths:
        expected = "___.._.._etc_passwd"
        assert paths.portable_filename("../../../etc/passwd") == expected

        # Unicode name are transliterated:
        expected = "This_contain_UMLAUT_umlauts.txt"
        assert paths.portable_filename("This contain UMLAUT \xfcml\xe4uts.txt") == expected

        # Check to see if illegal Windows filenames are properly handled
        for illegal_window_name in paths.ILLEGAL_WINDOWS_NAMES:
            # Rename files with names that are illegal on Windows
            expected = f"{illegal_window_name}_"
            assert paths.portable_filename(illegal_window_name) == expected

            # Allow files with names that are illegal on Windows
            assert paths.portable_filename(illegal_window_name, posix_only=True) == illegal_window_name

        # Check to see if the posix_only option does and does not replace
        # punctuation characters that are illegal in Windows filenames
        for valid_posix_path_char in paths.posix_legal_punctuation:
            test_name = f"test{valid_posix_path_char}"
            assert paths.portable_filename(test_name, posix_only=True) == test_name
            if valid_posix_path_char not in paths.legal_punctuation:
                expected = "test_"
                assert paths.portable_filename(test_name) == expected


class TestCommonPath(TestCase):
    def test_common_path_prefix1(self):
        test = paths.common_path_prefix("/a/b/c", "/a/b/c")
        assert test == ("a/b/c", 3)

    def test_common_path_prefix2(self):
        test = paths.common_path_prefix("/a/b/c", "/a/b")
        assert test == ("a/b", 2)

    def test_common_path_prefix3(self):
        test = paths.common_path_prefix("/a/b", "/a/b/c")
        assert test == ("a/b", 2)

    def test_common_path_prefix4(self):
        test = paths.common_path_prefix("/a", "/a")
        assert test == ("a", 1)

    def test_common_path_prefix_path_root(self):
        test = paths.common_path_prefix("/a/b/c", "/")
        assert test == (None, 0)

    def test_common_path_prefix_root_path(self):
        test = paths.common_path_prefix("/", "/a/b/c")
        assert test == (None, 0)

    def test_common_path_prefix_root_root(self):
        test = paths.common_path_prefix("/", "/")
        assert test == (None, 0)

    def test_common_path_prefix_path_elements_are_similar(self):
        test = paths.common_path_prefix("/a/b/c", "/a/b/d")
        assert test == ("a/b", 2)

    def test_common_path_prefix_no_match(self):
        test = paths.common_path_prefix("/abc/d", "/abe/f")
        assert test == (None, 0)

    def test_common_path_prefix_ignore_training_slashes(self):
        test = paths.common_path_prefix("/a/b/c/", "/a/b/c/")
        assert test == ("a/b/c", 3)

    def test_common_path_prefix8(self):
        test = paths.common_path_prefix("/a/b/c/", "/a/b")
        assert test == ("a/b", 2)

    def test_common_path_prefix10(self):
        test = paths.common_path_prefix("/a/b/c.txt", "/a/b/b.txt")
        assert test == ("a/b", 2)

    def test_common_path_prefix11(self):
        test = paths.common_path_prefix("/a/b/c.txt", "/a/b.txt")
        assert test == ("a", 1)

    def test_common_path_prefix12(self):
        test = paths.common_path_prefix("/a/c/e/x.txt", "/a/d/a.txt")
        assert test == ("a", 1)

    def test_common_path_prefix13(self):
        test = paths.common_path_prefix("/a/c/e/x.txt", "/a/d/")
        assert test == ("a", 1)

    def test_common_path_prefix14(self):
        test = paths.common_path_prefix("/a/c/e/", "/a/d/")
        assert test == ("a", 1)

    def test_common_path_prefix15(self):
        test = paths.common_path_prefix("/a/c/e/", "/a/c/a.txt")
        assert test == ("a/c", 2)

    def test_common_path_prefix16(self):
        test = paths.common_path_prefix("/a/c/e/", "/a/c/f/")
        assert test == ("a/c", 2)

    def test_common_path_prefix17(self):
        test = paths.common_path_prefix("/a/a.txt", "/a/b.txt/")
        assert test == ("a", 1)

    def test_common_path_prefix18(self):
        test = paths.common_path_prefix("/a/c/", "/a/")
        assert test == ("a", 1)

    def test_common_path_prefix19(self):
        test = paths.common_path_prefix("/a/c.txt", "/a/")
        assert test == ("a", 1)

    def test_common_path_prefix20(self):
        test = paths.common_path_prefix("/a/c/", "/a/d/")
        assert test == ("a", 1)

    def test_common_path_suffix(self):
        test = paths.common_path_suffix("/a/b/c", "/a/b/c")
        assert test == ("a/b/c", 3)

    def test_common_path_suffix_absolute_relative(self):
        test = paths.common_path_suffix("a/b/c", "/a/b/c")
        assert test == ("a/b/c", 3)

    def test_common_path_suffix_find_subpath(self):
        test = paths.common_path_suffix("/z/b/c", "/a/b/c")
        assert test == ("b/c", 2)

    def test_common_path_suffix_handles_relative_path(self):
        test = paths.common_path_suffix("a/b", "a/b")
        assert test == ("a/b", 2)

    def test_common_path_suffix_handles_relative_subpath(self):
        test = paths.common_path_suffix("zsds/adsds/a/b/b/c", "a//a/d//b/c")
        assert test == ("b/c", 2)

    def test_common_path_suffix_ignore_and_strip_trailing_slash(self):
        test = paths.common_path_suffix("zsds/adsds/a/b/b/c/", "a//a/d//b/c/")
        assert test == ("b/c", 2)

    def test_common_path_suffix_return_None_if_no_common_suffix(self):
        test = paths.common_path_suffix("/a/b/c", "/")
        assert test == (None, 0)

    def test_common_path_suffix_return_None_if_no_common_suffix2(self):
        test = paths.common_path_suffix("/", "/a/b/c")
        assert test == (None, 0)

    def test_common_path_suffix_match_only_whole_segments(self):
        # only segments are honored, commonality within segment is ignored
        test = paths.common_path_suffix("this/is/aaaa/great/path", "this/is/aaaaa/great/path")
        assert test == ("great/path", 2)

    def test_common_path_suffix_two_root(self):
        test = paths.common_path_suffix("/", "/")
        assert test == (None, 0)

    def test_common_path_suffix_empty_root(self):
        test = paths.common_path_suffix("", "/")
        assert test == (None, 0)

    def test_common_path_suffix_root_empty(self):
        test = paths.common_path_suffix("/", "")
        assert test == (None, 0)

    def test_common_path_suffix_empty_empty(self):
        test = paths.common_path_suffix("", "")
        assert test == (None, 0)
