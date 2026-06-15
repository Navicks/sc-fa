#!/usr/bin/env python3

import typer

from app.cli import site, token, user

app = typer.Typer()

app.add_typer(user.app, name="user", help="User management commands")
app.add_typer(site.app, name="site", help="Site management commands")
app.add_typer(token.app, name="token", help="Token management commands")


@app.command()
def version():
    """Show the version of the application."""
    from importlib.metadata import version

    print(f"sc_fa version: {version('sc_fa')}")


if __name__ == "__main__":
    app()
