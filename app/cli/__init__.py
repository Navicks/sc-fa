#!/usr/bin/env python3

import typer

from app.cli import site, user

app = typer.Typer()

app.add_typer(user.app, name="user", help="User management commands")
app.add_typer(site.app, name="site", help="Site management commands")

if __name__ == "__main__":
    app()
