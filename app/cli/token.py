import asyncio
from datetime import datetime
from typing import Annotated

import click
import typer
from pydantic import HttpUrl, ValidationError
from rich.console import Console
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.database import generate_async_session
from app.functions import export_model, import_model
from app.models.site import Site
from app.models.token import Token, TokenStatus, TokenType

app = typer.Typer()
console = Console()


@app.command(name="create", help="Create a new token")
def create(
    site_id: int,
    redirect_uri: str,
    token: TokenType,
    status_code: Annotated[
        TokenStatus,
        typer.Option("--status", "-s", help="Status of the token"),
    ] = TokenStatus.FOUND,
    subject: Annotated[
        str | None,
        typer.Option("--subject", "-j", help="Subject associated with this token"),
    ] = None,
    valid_from: Annotated[
        datetime | None,
        typer.Option("--valid-from", "-f", help="Date from which the token is valid"),
    ] = None,
    valid_to: Annotated[
        datetime | None,
        typer.Option("--valid-to", "-t", help="Date until which the token is valid"),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Only print the token value without additional messages",
            is_flag=True,
        ),
    ] = False,
) -> None:
    async def _create() -> None:
        async with generate_async_session() as session:
            try:
                site = (
                    await session.exec(select(Site).where(Site.id == site_id))
                ).first()
                if not site:
                    raise click.ClickException("No site found with specified id.")

                try:
                    token_row = Token(
                        site_id=site_id,
                        redirect_uri=HttpUrl(redirect_uri),
                        token=token,
                        status_code=status_code,
                        subject=subject,
                        valid_from=valid_from,
                        valid_to=valid_to,
                    )
                except ValidationError as e:
                    raise click.ClickException(
                        "Invalid input:\n"
                        + "\n".join(f"- {err['msg']}" for err in e.errors())
                    )

                session.add(token_row)
                await session.commit()
                if quiet:
                    return
                await session.refresh(token_row)
                console.print(
                    "[bold green]Token created successfully "
                    f"as {token_row.token}, ID: {token_row.id}[/bold green]"
                )
            except IntegrityError:
                await session.rollback()
                raise click.ClickException(
                    "A token with this value already exists "
                    f"for the specified site. - '{token}'"
                )

    asyncio.run(_create())


@app.command(name="update", help="Update an existing token")
def update(
    site_id: int,
    token: TokenType,
    redirect_uri: Annotated[
        str | None,
        typer.Option("--redirect-uri", "-r", help="New redirect URI for the token"),
    ] = None,
    status_code: Annotated[
        TokenStatus,
        typer.Option("--status", "-s", help="Status of the token"),
    ] = TokenStatus.FOUND,
    subject: Annotated[
        str | None,
        typer.Option("--subject", "-j", help="Subject associated with this token"),
    ] = None,
    valid_from: Annotated[
        datetime | None,
        typer.Option("--valid-from", "-f", help="Date from which the token is valid"),
    ] = None,
    valid_to: Annotated[
        datetime | None,
        typer.Option("--valid-to", "-t", help="Date until which the token is valid"),
    ] = None,
) -> None:
    async def _update() -> None:
        async with generate_async_session() as session:
            site = (await session.exec(select(Site).where(Site.id == id))).first()
            if not site:
                raise click.ClickException("No site found with specified id.")
            token_row = (
                await session.exec(
                    select(Token).where(Token.site_id == site_id, Token.token == token)
                )
            ).first()
            if not token_row:
                raise click.ClickException(
                    "No token found with this value "
                    "for the specified site."
                )

            try:
                if redirect_uri is not None:
                    token_row.redirect_uri = HttpUrl(redirect_uri)

                if subject is not None:
                    token_row.subject = subject
                if status_code is not None:
                    token_row.status_code = status_code
                if valid_from is not None:
                    token_row.valid_from = valid_from
                if valid_to is not None:
                    token_row.valid_to = valid_to
            except ValidationError as e:
                raise click.ClickException(
                    "Invalid input:\n"
                    + "\n".join(f"- {err['msg']}" for err in e.errors())
                )
            await session.commit()

    asyncio.run(_update())


@app.command(name="export", help="Export tokens with specified site ID to a file")
def export(
    site_id: int,
    format: Annotated[
        export_model.ExportFormat, typer.Option("--format", "-f", help="Export format")
    ] = export_model.ExportFormat.JSON,
    path: Annotated[str | None, typer.Argument(help="Output file path")] = None,
) -> None:
    async def _export() -> None:
        async with generate_async_session() as session:
            site = (await session.exec(select(Site).where(Site.id == site_id))).first()
            if not site:
                raise click.ClickException("No site found with specified id.")
            stmt = select(Token).where(Token.site_id == site_id)
            await export_model.export_models(session, Token, path, format, stmt=stmt)

    asyncio.run(_export())


@app.command(name="import", help="Import token(s) with specified site ID from a file")
def import_sites(
    site_id: int,
    format: Annotated[
        import_model.ImportFormat, typer.Option("--format", "-f", help="Import format")
    ] = import_model.ImportFormat.JSON,
    path: Annotated[str | None, typer.Argument(help="Input file path")] = None,
) -> None:
    async def _import() -> None:
        async with generate_async_session() as session:
            site = (await session.exec(select(Site).where(Site.id == site_id))).first()
            if not site:
                raise click.ClickException("No site found with specified id.")
            static_fields = {"site_id": site_id}
            await import_model.import_models(
                session,
                Token,
                path,
                format,
                static_fields=static_fields,
            )

    asyncio.run(_import())
