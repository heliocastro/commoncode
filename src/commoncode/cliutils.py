#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Iterator, MutableMapping, Sequence
from pathlib import Path
from typing import Any, TextIO

import click

# FIXME: this is NOT API
from click._termui_impl import ProgressBar
from click.termui import style
from click.types import BoolParamType
from click.utils import echo

# Tracing flags
TRACE = False


def logger_debug(*args: Any) -> None:
    pass


if TRACE:
    import logging

    logger = logging.getLogger(__name__)
    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)

    def logger_debug(*args: Any):
        return logger.debug(" ".join(isinstance(a, str) and a or repr(a) for a in args))


"""
Command line UI utilities for improved options, help and progress reporting.
"""


class BaseCommand(click.Command):
    """
    An enhanced click Command working around some Click quirk.
    """

    # override this in sub-classes with a command-specific message such as
    # "Try 'scancode --help' for help on options and arguments."
    short_usage_help = ""

    def get_usage(self, ctx: click.Context) -> str:
        """
        Ensure that usage points to the --help option explicitly.
        Workaround click issue https://github.com/mitsuhiko/click/issues/393
        """
        return super().get_usage(ctx) + self.short_usage_help

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        **extra: Any,
    ) -> Any:
        """
        Workaround click 4.0 bug https://github.com/mitsuhiko/click/issues/365
        """
        return click.Command.main(
            self,
            args=args,
            prog_name=self.name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            **extra,
        )


class GroupedHelpCommand(BaseCommand):
    """
    A command class that is aware of pluggable options that provides enhanced
    help where each option is grouped by group in the help.
    """

    short_usage_help = """
Try the '--help' option for help on options and arguments."""

    def __init__(
        self,
        name: str,
        context_settings: MutableMapping[str, Any] | None = None,
        callback: Callable[..., Any] | None = None,
        params: list[click.Parameter] | None = None,
        _help: str | None = None,
        epilog: str | None = None,
        short_help: str | None = None,
        options_metavar: str = "[OPTIONS]",
        add_help_option: bool = True,
        plugin_options: tuple[Any, ...] = (),  # noqa: F821
    ):
        """
        Create a new GroupedHelpCommand using the `plugin_options` list of
        PluggableCommandLineOption instances.
        """

        super().__init__(
            name,
            context_settings,
            callback,
            params,
            _help,
            epilog,
            short_help,
            options_metavar,
            add_help_option,
        )

        # this makes the options "known" to the command
        self.params.extend(plugin_options)

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Overridden from click.Command to write all options into the formatter in
        help_groups they belong to. If a group is not specified, add the option
        to MISC_GROUP group.
        """
        # this mapping defines the CLI help presentation order
        help_groups: dict[str, list[tuple[Any | int, tuple[str, str]]]] = {
            SCAN_GROUP: [],
            OTHER_SCAN_GROUP: [],
            SCAN_OPTIONS_GROUP: [],
            OUTPUT_GROUP: [],
            OUTPUT_FILTER_GROUP: [],
            OUTPUT_CONTROL_GROUP: [],
            PRE_SCAN_GROUP: [],
            POST_SCAN_GROUP: [],
            CORE_GROUP: [],
            MISC_GROUP: [],
            DOC_GROUP: [],
        }

        for param in self.get_params(ctx):
            # Get the list of option's name and help text
            help_record = param.get_help_record(ctx)
            if not help_record:
                continue
            # organize options by group
            help_group = getattr(param, "help_group", MISC_GROUP)
            sort_order = getattr(param, "sort_order", 100)
            help_groups[help_group].append((sort_order, help_record))

        with formatter.section("Options"):
            for group, help_records in help_groups.items():
                if not help_records:
                    continue
                with formatter.section(group):
                    sorted_records = [hr for _, hr in sorted(help_records)]
                    formatter.write_dl(sorted_records)


# overriden and copied from Click to work around Click woes for
# https://github.com/nexB/scancode-toolkit/issues/2583
class DebuggedProgressBar(ProgressBar[Any]):
    # overriden and copied from Click to work around Click woes for
    # https://github.com/nexB/scancode-toolkit/issues/2583
    def make_step(self, n_steps: int) -> None:
        # always increment
        self.pos += n_steps or 1
        super().make_step(n_steps)

    # overriden and copied from Click to work around Click woes for
    # https://github.com/nexB/scancode-toolkit/issues/2583
    def generator(self) -> Iterator[Any]:
        if self.is_hidden:
            yield from self.iter
        else:
            for rv in self.iter:
                self.current_item = rv
                self.update(1)
                self.render_progress()
                yield rv

            self.finish()
            self.render_progress()


class EnhancedProgressBar(DebuggedProgressBar):
    """
    Enhanced progressbar ensuring that nothing is displayed when the bar is hidden.
    """

    def render_progress(self) -> None:
        if not self.is_hidden:
            return super().render_progress()


class ProgressLogger(ProgressBar[Any]):
    """
    A subclass of Click ProgressBar providing a verbose line-by-line progress
    reporting.

    In contrast with the progressbar the label, percent, ETA, pos, bar_template
    and other formatting options are ignored.

    Progress information are printed as-is and no LF is added. The caller must
    provide an item_show_func to display some content and this must terminated
    with a line feed if needed.

    If no item_show_func is provided a simple dot is printed for each event.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.is_hidden = False

    def render_progress(self) -> None:
        line = self.format_progress_line()
        if line:
            # only add new lines if there is an item_show_func
            nl = bool(self.item_show_func)
            echo(line, file=self.file, nl=nl, color=self.color)
            self.file.flush()

    def format_progress_line(self) -> str:
        item_info = self.item_show_func(self.current_item) if self.item_show_func else "."
        return item_info if item_info else ""

    def render_finish(self) -> None:
        self.file.flush()


BAR_WIDTH = 20
BAR_SEP_LEN = len(" ")


def progressmanager(
    iterable: None | [] = None,
    length: int | None = None,
    fill_char: str = "#",
    empty_char: str = "-",
    bar_template: str = "%(bar)s",
    info_sep: str = " ",
    show_eta: bool = False,
    show_percent: bool | None = False,
    show_pos: bool = True,
    item_show_func: Callable | None = None,
    label: str | None = None,
    file: TextIO | None = None,
    color: bool | None = None,  # NOQA
    update_min_steps: int = 1,
    width: int = BAR_WIDTH,
    verbose: bool = False,
) -> ProgressLogger | EnhancedProgressBar:
    """
    Return an iterable context manager showing progress as a progress bar
    (default) or item-by-item log (if verbose is True) while iterating.

    It's arguments are similar to Click.termui.progressbar with these new
    arguments added at the end of the signature:

    :param verbose:  if True, display a progress log. Otherwise, a progress bar.
    """

    kwargs = {
        "iterable": iterable,
        "length": length,
        "fill_char": fill_char,
        "empty_char": empty_char,
        "bar_template": bar_template,
        "info_sep": info_sep,
        "show_eta": show_eta,
        "show_percent": show_percent,
        "show_pos": show_pos,
        "item_show_func": item_show_func,
        "label": label,
        "file": file,
        "color": color,
        "width": width,
    }

    if verbose:
        return ProgressLogger(**kwargs)
    else:
        bar_template = "[%(bar)s]" + " " + "%(info)s" if bar_template is None else bar_template
        return EnhancedProgressBar(**kwargs)


def fixed_width_file_name(path: Path, max_length: int = 25) -> str:
    """
    Return a fixed width file name of at most `max_length` characters computed
    from the `path` string and usable for fixed width display. If the `path`
    file name is longer than `max_length`, the file name is truncated in the
    middle using three dots "..." as an ellipsis and the ext is kept.

    For example:
    >>> fwfn = fixed_width_file_name('0123456789012345678901234.c')
    >>> assert fwfn == '0123456789...5678901234.c'
    >>> fwfn = fixed_width_file_name('some/path/0123456789012345678901234.c')
    >>> assert fwfn == '0123456789...5678901234.c'
    >>> fwfn = fixed_width_file_name('some/sort.c')
    >>> assert fwfn == 'sort.c'
    >>> fwfn = fixed_width_file_name('some/123456', max_length=5)
    >>> assert fwfn == ''
    """
    if not path:
        return ""

    if len(path.name) <= max_length:
        return path.name
    base_name, ext = path.stem, path.suffix
    dots = 3
    len_ext = len(ext)
    remaining_length = max_length - len_ext - dots

    if remaining_length < 5 or remaining_length < (len_ext + dots):
        return ""

    prefix_and_suffix_length = abs(remaining_length // 2)
    prefix = base_name[:prefix_and_suffix_length]
    ellipsis = dots * "."
    suffix = base_name[-prefix_and_suffix_length:]
    return "{prefix}{ellipsis}{suffix}{ext}".format(**locals())


def file_name_max_len(used_width: int = BAR_WIDTH + 1 + 7 + 1 + 8 + 1) -> int:
    """
    Return the max length of a path given the current terminal width.

    A progress bar is composed of these elements:
    [-----------------------------------#]  1667  Scanned: tu-berlin.yml
    - the bar proper which is BAR_WIDTH characters
    - one space
    - the number of files. We set it to 7 chars, eg. 9 999 999 files
    - one space
    - the word Scanned: 8 chars
    - one space
    - the file name proper
    The space usage is therefore:
        BAR_WIDTH + 1 + 7 + 1 + 8 + 1 + the file name length
    """
    term_width, _height = shutil.get_terminal_size()
    max_filename_length = term_width - used_width
    return max_filename_length


def path_progress_message(item: list[str] | None = None, verbose: bool = False, prefix: str = "Scanned: ") -> str:
    """
    Return a styled message suitable for progress display when processing a path
    for an `item` tuple of (location, rid, scan_errors, *other items)
    """
    if not item:
        return ""
    location: Path = Path(item[0])
    errors = item[2]
    progress_line: str = location.name
    if not verbose:
        max_file_name_len = file_name_max_len()
        # do not display a file name in progress bar if there is no space available
        if max_file_name_len <= 10:
            return ""
        progress_line = fixed_width_file_name(location, max_file_name_len)

    color = "red" if errors else "green"
    return style(prefix) + style(progress_line, fg=color)


# CLI help groups
SCAN_GROUP = "primary scans"
SCAN_OPTIONS_GROUP = "scan options"
OTHER_SCAN_GROUP = "other scans"
OUTPUT_GROUP = "output formats"
OUTPUT_CONTROL_GROUP = "output control"
OUTPUT_FILTER_GROUP = "output filters"
PRE_SCAN_GROUP = "pre-scan"
POST_SCAN_GROUP = "post-scan"
MISC_GROUP = "miscellaneous"
DOC_GROUP = "documentation"
CORE_GROUP = "core"


class PluggableCommandLineOption(click.Option):
    """
    An option with extra args and attributes to control CLI help options
    grouping, co-required and conflicting options (e.g. mutually exclusive).
    This option is also pluggable e.g. providable by a plugin.
    """

    # args are from Click 8.x
    def __init__(
        self,
        param_decls: list[str] | None = None,
        show_default: bool | str | None = False,
        prompt: bool | str = False,
        confirmation_prompt: bool | str = False,
        hide_input: bool = False,
        is_flag: bool | None = None,
        flag_value: Any | None = None,
        multiple: bool = False,
        count: bool = False,
        allow_from_autoenv: bool = True,
        _type: click.ParamType | Any | None = None,
        _help: str | None = None,
        hidden: bool = False,
        # custom additions #
        # a string that set the CLI help group for this option
        help_group: str = MISC_GROUP,
        # a relative sort order number (integer or float) for this
        # option within a help group: the sort is by increasing
        # sort_order then by option declaration.
        sort_order: int = 100,
        # a sequence of other option name strings that this option
        # requires to be set
        required_options: dict[str, str] = {},
        # a sequence of other option name strings that this option
        # conflicts with if they are set
        conflicting_options: dict[str, str] = {},
        **kwargs: Any,
    ) -> None:
        super().__init__(
            param_decls=param_decls,
            show_default=show_default,
            prompt=prompt,
            confirmation_prompt=confirmation_prompt,
            hide_input=hide_input,
            is_flag=is_flag,
            flag_value=flag_value,
            multiple=multiple,
            count=count,
            allow_from_autoenv=allow_from_autoenv,
            type=_type,
            help=_help,
            **kwargs,
        )

        self.help_group = help_group
        self.sort_order = sort_order
        self.required_options = required_options
        self.conflicting_options = conflicting_options
        self.hidden = hidden

    def __repr__(self, *args: Any, **kwargs: Any) -> str:
        name: str | None = self.name
        opt: str = self.opts[-1]
        help_group: str = self.help_group
        required_options: dict[str, str] = self.required_options
        conflicting_options: dict[str, str] = self.conflicting_options

        return (
            "PluggableCommandLineOption<name={name!r}, "
            "required_options={required_options!r}, "
            "conflicting_options={conflicting_options!r}>".format(**locals())
        )

    def validate_dependencies(self, ctx: click.Context, value: str) -> None:
        """
        Validate `value` against declared `required_options` or
        `conflicting_options` dependencies.
        """
        _validate_option_dependencies(ctx, self, value, self.required_options, required=True)
        _validate_option_dependencies(ctx, self, value, self.conflicting_options, required=False)

    def get_help_record(self, ctx: click.Context) -> tuple[str, str] | None:
        if not self.hidden:
            return click.Option.get_help_record(self, ctx)
        return None


def validate_option_dependencies(ctx: click.Context) -> None:
    """
    Validate all PluggableCommandLineOption dependencies in the `ctx` Click
    context. Ignore eager flags.
    """
    values = ctx.params
    if TRACE:
        logger_debug("validate_option_dependencies: values:")
        for va in sorted(values.items()):
            logger_debug("  ", va)

    for param in ctx.command.params:
        if param.is_eager:
            continue
        if not isinstance(param, PluggableCommandLineOption):
            if TRACE:
                logger_debug("  validate_option_dependencies: skip param:", param)
            continue
        if param.name:
            value = values.get(param.name)
            if TRACE:
                logger_debug("  validate_option_dependencies: param:", param, "value:", value)
            if isinstance(value, str):
                param.validate_dependencies(ctx, value)


def _validate_option_dependencies(
    ctx: click.Context,
    param: PluggableCommandLineOption,
    value: str,
    other_option_names: dict[str, str] | None,
    required: bool = False,
) -> str | None:
    """
    Validate the `other_option_names` option dependencies and return a
    UsageError if the `param` `value` is set to a not-None non-default value and
    if:
    - `required` is True and the `other_option_names` options are not set with a
       not-None value in the `ctx` context.
    - `required` is False and any of the `other_option_names` options are set
       with a not-None, non-default value in the `ctx` context.
    """
    if not other_option_names:
        return None

    def _is_set(_value: str, _param: PluggableCommandLineOption) -> bool | str:
        if _param.type in (bool, BoolParamType):
            return _value

        empty = _value and len(_value) == 0 or not _value if _param.multiple else _value is None

        return bool(not empty and _value != _param.default)

    is_set = _is_set(value, param)

    if TRACE:
        logger_debug()
        logger_debug("Checking param:", param)
        logger_debug("  value:", value, "is_set:", is_set)

    if not is_set:
        return None

    oparams_by_name = {oparam.name: oparam for oparam in ctx.command.params}
    oparams = []
    missing_onames = []

    for oname in other_option_names:
        oparam = oparams_by_name.get(oname)
        if not oparam:
            missing_onames.append(oparam)
        else:
            oparams.append(oparam)

    if TRACE:
        logger_debug()
        logger_debug("  Available other params:")
        for oparam in oparams:
            logger_debug("    other param:", oparam)
            logger_debug("      value:", ctx.params.get(oparam.name))
        if required:
            logger_debug("    missing names:", missing_onames)

    if required and missing_onames:
        opt = param.opts[-1]
        oopts = [oparam.opts[-1] for oparam in oparams]
        omopts = ["--" + oname.replace("_", "-") for oname in missing_onames]
        oopts.extend(omopts)
        oopts = ", ".join(oopts)
        msg = (
            "The option %(opt)s requires the option(s) %(all_opts)s."
            "and is missing %(omopts)s. "
            "You must set all of these options if you use this option." % locals()
        )
        raise click.UsageError(msg)

    if TRACE:
        logger_debug()
        logger_debug("  Checking other params:")

    opt = param.opts[-1]

    for oparam in oparams:
        ovalue = ctx.params.get(oparam.name)
        ois_set = _is_set(ovalue, oparam)

        if TRACE:
            logger_debug("    Checking oparam:", oparam)
            logger_debug("      value:", ovalue, "ois_set:", ois_set)

        # by convention the last opt is the long form
        oopt = oparam.opts[-1]
        oopts = ", ".join(oparam.opts[-1] for oparam in oparams)
        all_opts = "%(opt)s and %(oopts)s" % locals()
        if required and not ois_set:
            msg = (
                "The option %(opt)s requires the option(s) %(oopts)s "
                "and is missing %(oopt)s. "
                "You must set all of these options if you use this option." % locals()
            )
            raise click.UsageError(msg)

        if not required and ois_set:
            msg = (
                "The option %(opt)s cannot be used together with the %(oopts)s option(s) "
                "and %(oopt)s is used. "
                "You can set only one of these options at a time." % locals()
            )
            raise click.UsageError(msg)
    return None
