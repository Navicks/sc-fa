import inspect
from typing import TypeAlias

import aiofiles
from aiofiles.threadpool.text import AsyncTextIndirectIOWrapper, AsyncTextIOWrapper

AioTextFile: TypeAlias = AsyncTextIOWrapper | AsyncTextIndirectIOWrapper


async def open_input_file(
    path: str | None,
) -> AioTextFile:
    if path is None or path in ("", "-", "/dev/stdin"):
        return aiofiles.stdin
    return await aiofiles.open(path, "r", encoding="utf-8")


async def open_output_file(
    path: str | None,
) -> AioTextFile:
    if path is None or path in ("", "-", "/dev/stdout"):
        return aiofiles.stdout
    return await aiofiles.open(path, "w", encoding="utf-8")


async def close(f: AioTextFile) -> None:
    if f in (aiofiles.stdin, aiofiles.stdout, aiofiles.stderr):
        return

    close_fn = getattr(f, "close", None)
    if close_fn is None:
        return

    result = close_fn()
    if inspect.isawaitable(result):
        await result
