#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

from typing import Any

import attr
from attr.validators import in_ as choices  # NOQA

"""
Utilities and helpers for data classes.
"""

HELP_METADATA: str = "__field_help"
LABEL_METADATA: str = "__field_label"


def attribute(
    default: Any = attr.NOTHING,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    init: bool = True,
    _type: Any | None = None,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
    metadata: dict[Any, Any] | None = None,
) -> attr.Attribute:  # NOQA
    """
    A generic attribute with help metadata and that is not included in the
    representation by default.
    """
    metadata = metadata or {}
    if _help:
        metadata[HELP_METADATA] = _help

    if label:
        metadata[LABEL_METADATA] = label

    return attr.attrib(
        default=default,
        validator=validator,
        repr=_repr,
        eq=eq,
        order=order,
        init=init,
        metadata=metadata,
        type=_type,
        converter=converter,
    )


def Boolean(
    default: bool = False,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A boolean attribute.
    """
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=bool,
        converter=converter,
        _help=_help,
        label=label,
    )


def TriBoolean(
    default: bool = False,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A tri-boolean attribute with possible values of None, True and False.
    """
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=bool,
        converter=converter,
        _help=_help,
        label=label,
    )


def String(
    default: str | None = None,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A string attribute.
    """
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=str,
        converter=converter,
        _help=_help,
        label=label,
    )


def Integer(
    default: int = 0,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    An integer attribute.
    """
    converter = converter or attr.converters.optional(int)
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=int,
        converter=converter,
        _help=_help,
        label=label,
    )


def Float(
    default: float = 0.0,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A float attribute.
    """
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=float,
        converter=converter,
        _help=_help,
        label=label,
    )


def List(
    item_type: Any = Any,
    default: Any = attr.Factory(list),
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A list attribute: the optional item_type defines the type of items it stores.
    """
    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=list[item_type],
        converter=converter,
        _help=_help,
        label=label,
    )


def Mapping(
    value_type: Any = Any,
    default: Any = attr.Factory(dict),
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A mapping attribute: the optional value_type defines the type of values it
    stores. The key is always a string.

    Notes: in Python 2 the type is Dict as there is no typing available for
    dict for now.
    """
    if default is attr.NOTHING:
        default = attr.Factory(dict)

    return attribute(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        init=True,
        _type=dict[str, value_type],
        converter=converter,
        _help=_help,
        label=label,
    )


##################################################
# FIXME: add proper support for dates!!!
##################################################


def Date(
    default: Any = None,
    validator: Any | None = None,
    _repr: bool = False,
    eq: bool = True,
    order: bool = True,
    converter: Any | None = None,
    _help: str | None = None,
    label: str | None = None,
) -> attr.Attribute:
    """
    A date attribute. It always serializes to an ISO date string.
    Behavior is TBD and for now this is exactly a string.
    """
    return String(
        default=default,
        validator=validator,
        _repr=_repr,
        eq=eq,
        order=order,
        converter=converter,
        _help=_help,
        label=label,
    )
