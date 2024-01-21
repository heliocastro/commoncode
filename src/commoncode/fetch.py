#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, InvalidSchema

from commoncode import fileutils

logger = logging.getLogger(__name__)
# import sys
# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
# logger.setLevel(logging.DEBUG)


def download_url(url: str, file_name: str | None = None, verify: bool = True, timeout: int = 10) -> str:
    """
    Fetch `url` and return the temporary location where the fetched content was
    saved. Use `file_name` if provided or create a new `file_name` base on the last
    url segment. If `verify` is True, SSL certification is performed. Otherwise, no
    verification is done but a warning will be printed.
    `timeout` is the timeout in seconds.
    """
    requests_args: dict[str, Any] = {"timeout": timeout, "verify": verify}
    if not file_name:
        parsed_url = urlparse(url).path.split("/")
        file_name = parsed_url[-1] if parsed_url else ""

    try:
        response = requests.get(url, timeout=timeout, **requests_args)
    except (ConnectionError, InvalidSchema):
        logger.error("download_url: Download failed for {url!r}".format(**locals()))
        raise

    status = response.status_code
    if status != 200:
        msg = "download_url: Download failed for {url!r} with {status!r}".format(**locals())
        logger.error(msg)
        raise Exception(msg)

    output_file: Path = fileutils.get_temp_dir(prefix="fetch-") / file_name
    with output_file.open("wb") as out:
        out.write(response.content)

    return output_file.as_posix()


def ping_url(url: str) -> bool:
    """
    Returns True is `url` is reachable.
    """

    # FIXME: if there is no 200 HTTP status, then the ULR may not be reachable.
    try:
        requests.get(url, timeout=10)
    except Exception:
        return False
    else:
        return True
