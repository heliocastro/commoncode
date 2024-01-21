#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import calendar
from datetime import datetime
from pathlib import Path


def isoformat(utc_date: datetime) -> str:
    return datetime.isoformat(utc_date).replace("T", " ")


def get_file_mtime(location: Path, iso: bool = True) -> str | None:
    """
    Return a string containing the last modified date of a file formatted
    as an ISO time stamp if ISO is True or as a raw number since epoch.
    """
    date: str | None = None

    if not location.is_dir():
        mtime = location.stat().st_mtime
        if iso:
            utc_date = datetime.utcfromtimestamp(mtime)
            date = isoformat(utc_date)
        else:
            date = str(mtime)
    return date


def secs_from_epoch(d: str) -> int:
    """
    Return a number of seconds since epoch for a date time stamp
    """
    # FIXME: what does this do?
    return calendar.timegm(datetime.strptime(d.split(".")[0], "%Y-%m-%d %H:%M:%S").timetuple())
