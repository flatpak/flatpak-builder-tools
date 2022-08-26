from types import TracebackType
from typing import AsyncIterator, ClassVar, ContextManager, Optional, Tuple, Type

import contextlib
import os

from rich.console import Console, RenderableType
from rich.progress import Progress, TaskID

import aiohttp

from .cache import Cache

DEFAULT_PART_SIZE = 4096


def _format_bytes_as_mb(n: int) -> str:
    return f'{n/1024/1024:.2f} MiB'


class _ResponseStream(ContextManager['_ResponseStream']):
    _MINIMUM_SIZE_FOR_LIVE_PROGRESS = 1 * 1024 * 1024

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        progress: Optional[Progress],
    ) -> None:
        self._response = response

        self._task: Optional[TaskID] = None
        self._read = 0
        self._total = 0
        self._progress_task: Optional[Tuple[Progress, TaskID]] = None
        if (
            progress is not None
            and response.content_length is not None
            and response.content_length > self._MINIMUM_SIZE_FOR_LIVE_PROGRESS
        ):
            self._total = response.content_length
            task = progress.add_task('', total=self._total, start=False)
            self._progress_task = (progress, task)
            self._update_progress()
            progress.start_task(task)

    def __enter__(self) -> '_ResponseStream':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._progress_task is not None:
            progress, task = self._progress_task
            progress.remove_task(task)

    def _update_progress(self) -> None:
        if self._progress_task is None:
            return

        assert self._total

        progress, task = self._progress_task
        mb_read = _format_bytes_as_mb(self._read)
        mb_total = _format_bytes_as_mb(self._total)
        progress.update(
            task,
            completed=self._read,
            description=f'{os.path.basename(self._response.url.path)} [{mb_read}/{mb_total}]',
        )

    async def read(self, n: int = -1) -> bytes:
        data = await self._response.content.read(n)
        self._read += len(data)
        self._update_progress()

        return data


class Requests:
    instance: 'Requests'

    DEFAULT_RETRIES = 5
    retries: ClassVar[int] = DEFAULT_RETRIES

    def __init__(self) -> None:
        self.progress: Optional[Progress] = None

    def __get_cache_bucket(self, cachable: bool, url: str) -> Cache.BucketRef:
        return Cache.get_working_instance_if(cachable).get(f'requests:{url}')

    @contextlib.asynccontextmanager
    async def _open_stream(self, url: str) -> AsyncIterator[_ResponseStream]:
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            async with session.get(url) as response:
                with _ResponseStream(response, self.progress) as stream:
                    yield stream

    async def _read_parts(
        self, url: str, size: int = DEFAULT_PART_SIZE
    ) -> AsyncIterator[bytes]:
        async with self._open_stream(url) as stream:
            while True:
                data = await stream.read(size)
                if not data:
                    return

                yield data

    async def _read_all(self, url: str) -> bytes:
        async with self._open_stream(url) as stream:
            return await stream.read()

    async def read_parts(
        self, url: str, *, cachable: bool = False, size: int = DEFAULT_PART_SIZE
    ) -> AsyncIterator[bytes]:
        bucket = self.__get_cache_bucket(cachable, url)

        bucket_reader = bucket.open_read()
        if bucket_reader is not None:
            for part in bucket_reader.read_parts(size):
                yield part

            return

        for i in range(1, Requests.retries + 1):
            try:
                with bucket.open_write() as bucket_writer:
                    async for part in self._read_parts(url, size):
                        bucket_writer.write(part)
                        yield part

                return
            except Exception:
                if i == Requests.retries:
                    raise

    async def read_all(self, url: str, *, cachable: bool = False) -> bytes:
        bucket = self.__get_cache_bucket(cachable, url)

        bucket_reader = bucket.open_read()
        if bucket_reader is not None:
            return bucket_reader.read_all()

        for i in range(1, Requests.retries + 1):
            try:
                with bucket.open_write() as bucket_writer:
                    data = await self._read_all(url)
                    bucket_writer.write(data)
                    return data
            except Exception:
                if i == Requests.retries:
                    raise

        assert False

    def get_renderable(self, console: Console) -> RenderableType:
        if self.progress is not None:
            assert self.progress.console is console
        else:
            self.progress = Progress(console=console)

        return self.progress


class StubRequests(Requests):
    async def _read_parts(
        self, url: str, size: int = DEFAULT_PART_SIZE
    ) -> AsyncIterator[bytes]:
        yield b''

    async def _read_all(self, url: str) -> bytes:
        return b''


Requests.instance = Requests()
