from dataclasses import dataclass
from typing import Collection, ContextManager, Optional, Set, Type

import asyncio
import shutil
import sys
import traceback
import types

from rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderableType,
    RenderResult,
)
from rich.measure import Measurement
from rich.segment import Segment
from rich.status import Status

from .package import Package
from .providers import ModuleProvider


def _generating_packages(finished: int, total: int) -> str:
    return f'Generating packages [{finished}/{total}]'


class _GeneratingPackagesRenderable(ConsoleRenderable):
    def __init__(self, finished: int, total: int, processing: Set[Package]) -> None:
        self.generating_string = _generating_packages(finished, total)
        self.processing = processing

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return Measurement(0, options.max_width)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        ARROW = ' => '
        ELLIPSES = '...'
        SEPARATOR = ', '

        yield Segment(self.generating_string)
        space_remaining = options.max_width - len(self.generating_string)

        generating_string_width = len(self.generating_string)
        if space_remaining < len(ELLIPSES):
            return
        elif options.max_width < len(ELLIPSES) + len(ARROW):
            return ELLIPSES

        packages = sorted(
            f'{package.name} @ {package.version}' for package in self.processing
        )

        yield Segment(ARROW)
        space_remaining -= len(ARROW) + len(ELLIPSES)

        for i, package in enumerate(packages):
            if i:
                package = SEPARATOR + package
            if len(package) > space_remaining:
                break

            yield Segment(package)
            space_remaining -= len(package)

        yield Segment(ELLIPSES)


class GeneratorProgress(ContextManager['GeneratorProgress']):
    def __init__(
        self,
        packages: Collection[Package],
        module_provider: ModuleProvider,
        *,
        max_parallel: int,
        traceback_on_interrupt: bool,
    ) -> None:
        self.finished = 0
        self.processing: Set[Package] = set()
        self.packages = packages
        self.module_provider = module_provider
        self.parallel_limit = asyncio.Semaphore(max_parallel)
        self.traceback_on_interrupt = traceback_on_interrupt
        self.status: Optional[Status] = None

    @property
    def _total(self) -> int:
        return len(self.packages)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        tb: Optional[types.TracebackType],
    ) -> None:
        line = f'Generated {self._total} package(s).'
        if self.status is not None:
            self.status.update(line)
            self.status.stop()
        else:
            print(line)

    def _update(self) -> None:
        if self.status is None:
            # No TTY. Only print an update on multiples of 10 to avoid spamming
            # the console.
            if self.finished % 10 == 0 or self.finished == self._total:
                print(
                    f'{_generating_packages(self.finished, self._total)}...',
                    flush=True,
                )
            return

        self.status.update(
            _GeneratingPackagesRenderable(self.finished, self._total, self.processing)
        )

    async def _generate(self, package: Package) -> None:
        async with self.parallel_limit:
            self.processing.add(package)
            # Don't bother printing an update here without live progress, since
            # then the currently processing packages won't appear anyway.
            if self.status is not None:
                self._update()

            try:
                await self.module_provider.generate_package(package)
            except asyncio.CancelledError:
                if self.traceback_on_interrupt:
                    print(f'========== {package.name} ==========', file=sys.stderr)
                    traceback.print_exc()
                    print(file=sys.stderr)
                raise

            self.finished += 1
            self.processing.remove(package)
            self._update()

    def get_renderable(self, console: Console) -> RenderableType:
        if self.status is not None:
            assert self.status.console is console
        else:
            self.status = Status('', console=console)

        return self.status

    async def run(self) -> None:
        self._update()

        tasks = [asyncio.create_task(self._generate(pkg)) for pkg in self.packages]
        for coro in asyncio.as_completed(tasks):
            try:
                await coro
            except:
                # If an exception occurred, make sure to cancel all the other
                # tasks.
                for task in tasks:
                    task.cancel()

                raise
