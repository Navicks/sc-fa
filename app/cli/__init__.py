#!/usr/bin/env python3

import typer

from app.cli import user


app = typer.Typer()

app.add_typer(user.app, name="user", help="User management commands")


if __name__ == "__main__":
    app()
