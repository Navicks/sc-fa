import sys
from typing import TextIO


def open_input_file(path: str | None) -> TextIO:
    return (
        open(path, "r", encoding="utf-8")
        if path is not None and path not in ("", "-", "/dev/stdin")
        else sys.stdin
    )


def open_output_file(path: str | None) -> TextIO:
    return (
        open(path, "w", encoding="utf-8")
        if path is not None and path not in ("", "-", "/dev/stdout")
        else sys.stdout
    )


def close(f: TextIO) -> None:
    if f not in (sys.stdin, sys.stdout, sys.stderr):
        f.close()
