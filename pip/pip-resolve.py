#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve dependencies for a list of requirements.

***********************************

Created on 2022/08/25 at 10:01:51

Copyright (C) 2022 real-yfprojects (github.com user)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import pprint
import sys
from contextlib import ExitStack
from typing import Any, Dict, cast

from pip._internal.commands.download import (DownloadCommand, TempDirectory,
                                             ensure_dir, get_build_tracker,
                                             make_target_python,
                                             normalize_path)
from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.resolvelib.resolver import (
    Candidate, PipProvider, PipReporter, Requirement, ResolutionImpossible,
    RLResolver)
from pip._internal.utils.temp_dir import global_tempdir_manager
from pip._vendor.resolvelib.structs import DirectedGraph

fprint = pprint.pprint


def resolve_dependencies(package_name: str, download_dir: str):
    with ExitStack() as context_stack:
        # init and parse cmd options
        download_command = DownloadCommand(name='download', summary='')
        options, args = download_command.parse_args(
            ['--dest', download_dir, package_name])

        # override/process some options
        options.ignore_installed = True
        options.editables = []
        options.download_dir = normalize_path(options.download_dir)
        ensure_dir(options.download_dir)

        # make resolver
        context_stack.enter_context(download_command.main_context())
        context_stack.enter_context(global_tempdir_manager())

        session = download_command.get_default_session(options)

        target_python = make_target_python(options)
        finder = download_command._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )

        build_tracker = download_command.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="download",
            globally_managed=True,
        )

        preparer = download_command.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.download_dir,
            use_user_site=False,
            verbosity=3,
        )

        resolver = download_command.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            ignore_requires_python=options.ignore_requires_python,
            use_pep517=options.use_pep517,
            py_version_info=options.python_version,
        )

        # download_command.trace_basic_info(finder)

        # process requirements
        reqs = download_command.get_requirements(args, options, finder,
                                                 session)

        # resolve dependencies
        graph: DirectedGraph
        mapping, graph, criteria = resolve(resolver, reqs, True)

        # dependencies per package

        def dict_from_node(graph: DirectedGraph, node: Any):
            d: Dict[Any, dict] = {}
            for n in graph.iter_children(node):
                if n == '<Python from Requires-Python>':
                    continue
                d.setdefault(n, {}).update(dict_from_node(graph, n))
            return d

        fprint(dict_from_node(graph, None))


def resolve(resolver, reqs, check_wheels):

    collected = resolver.factory.collect_root_requirements(reqs)
    provider = PipProvider(
        factory=resolver.factory,
        constraints=collected.constraints,
        ignore_dependencies=resolver.ignore_dependencies,
        upgrade_strategy=resolver.upgrade_strategy,
        user_requested=collected.user_requested,
    )
    reporter = PipReporter()
    resolver: RLResolver[Requirement, Candidate, str] = RLResolver(
        provider,
        reporter,
    )

    try:
        try_to_avoid_resolution_too_deep = 2000000
        result = resolver._result = resolver.resolve(
            collected.requirements,
            max_rounds=try_to_avoid_resolution_too_deep)

    except ResolutionImpossible as e:
        error = resolver.factory.get_installation_error(
            cast("ResolutionImpossible[Requirement, Candidate]", e),
            collected.constraints,
        )
        raise error from e

    return result


if __name__ == '__main__':
    resolve_dependencies(*sys.argv[1:3])
