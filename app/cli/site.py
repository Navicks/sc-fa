import asyncio
from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.database import generate_async_session
from app.functions import export_model, import_model
from app.models.site import Site

app = typer.Typer()
console_err = Console(stderr=True)


@app.command(name="create", help="Create a new site")
def create(
    fqdn: str,
    name: str,
) -> None:
    async def _create() -> None:
        async with generate_async_session() as session:
            try:
                site = Site(
                    fqdn=fqdn,
                    name=name,
                )
                session.add(site)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                console_err.print(
                    "[bold red]A site with this fqdn already exists.[/bold red]"
                )
                raise typer.Exit(code=1)

    asyncio.run(_create())


@app.command(name="update", help="Update an existing site")
def update(
    id: int,
    fqdn: str,
    name: str,
) -> None:
    async def _update() -> None:
        async with generate_async_session() as session:
            site = (await session.exec(select(Site).where(Site.id == id))).first()
            if not site:
                console_err.print(
                    "[bold red]No site found with this id.[/bold red]"
                )
                raise typer.Exit(code=1)
            site.fqdn = fqdn
            site.name = name
            await session.commit()
    asyncio.run(_update())


@app.command(name="export", help="Export all sites to a file")
def export(
    format: Annotated[
        export_model.ExportFormat, typer.Option("--format", "-f", help="Export format")
    ] = export_model.ExportFormat.JSON,
    path: Annotated[
        str | None,
        typer.Argument(help="Output file path")
    ] = None,
) -> None:
    async def _export() -> None:
        async with generate_async_session() as session:
            await export_model.export_models(
                session, Site, path, format
            )
    asyncio.run(_export())


@app.command(name="import", help="Import site from a file")
def import_sites(
    format: Annotated[
        import_model.ImportFormat, typer.Option("--format", "-f", help="Import format")
    ] = import_model.ImportFormat.JSON,
    path: Annotated[
        str | None,
        typer.Argument(help="Input file path")
    ] = None,
) -> None:
    async def _import() -> None:
        async with generate_async_session() as session:
            await import_model.import_models(session, Site, path, format)
    asyncio.run(_import())
