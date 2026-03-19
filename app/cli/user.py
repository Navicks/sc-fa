import asyncio
from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.cache import user as cache_user
from app.database import generate_async_session
from app.database.redis import create_redis_client
from app.functions import export_model, import_model
from app.models.user import User
from app.models.user_site import UserSite

app = typer.Typer()
console_err = Console(stderr=True)


@app.command(name="create", help="Create a new user")
def create(
    email: str,
    password: Annotated[
        str, typer.Option(prompt=True, hide_input=True, confirmation_prompt=True)
    ],
    display_name: str,
    is_admin: bool = False,
) -> None:
    async def _create() -> None:
        async with generate_async_session() as session:
            try:
                user = User(
                    email=email,
                    display_name=display_name,
                    disabled=False,
                    is_admin=is_admin,
                )
                user.set_password(password)
                session.add(user)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                console_err.print(
                    "[bold red]A user with this email already exists.[/bold red]"
                )
                raise typer.Exit(code=1)

    asyncio.run(_create())


@app.command(name="change-password", help="Change a user's password")
def change_password(
    email: str,
    password: Annotated[
        str | None,
        typer.Option(
            "--password",
            "-p",
            help=(
                "New password. If omitted, you will be prompted after the user is "
                "validated."
            ),
        ),
    ] = None,
) -> None:
    async def _change_password(password: str | None) -> None:
        async with generate_async_session() as session:
            user = (await session.exec(select(User).where(User.email == email))).first()
            if not user:
                console_err.print("[bold red]No user found with this email.[/bold red]")
                raise typer.Exit(code=1)

            if password is None:
                password = typer.prompt(
                    "New password",
                    hide_input=True,
                    confirmation_prompt=True,
                )

            user.set_password(password)
            await cache_user.delete(create_redis_client(), user)
            await session.commit()
            console_err.print("[bold green]Password updated successfully.[/bold green]")

    asyncio.run(_change_password(password))


@app.command(name="update", help="Update an existing user")
def update(
    email: str,
    display_name: Annotated[
        str | None,
        typer.Option(
            "--display-name",
            "-d",
            help="New display name. If omitted, the current display name will be kept.",
        ),
    ] = None,
    is_admin: Annotated[
        bool | None,
        typer.Option(
            "--is-admin/--no-is-admin",
            "-a",
            help="Set the user as an admin. If omitted, "
            "the current admin status will be kept.",
        ),
    ] = None,
    disabled: Annotated[
        bool | None,
        typer.Option(
            "--disabled/--no-disabled",
            "-D",
            help="Disable the user. If omitted, "
            "the current disabled status will be kept.",
        ),
    ] = None,
) -> None:
    async def _update() -> None:
        async with generate_async_session() as session:
            user = (await session.exec(select(User).where(User.email == email))).first()
            if not user:
                console_err.print("[bold red]No user found with this email.[/bold red]")
                raise typer.Exit(code=1)

            if display_name is not None:
                user.display_name = display_name
            if is_admin is not None:
                user.is_admin = is_admin
            if disabled is not None:
                user.disabled = disabled
            await cache_user.delete(create_redis_client(), user)
            await session.commit()
            console_err.print("[bold green]User updated successfully.[/bold green]")

    asyncio.run(_update())


@app.command(name="delete", help="Delete a user")
def delete(email: str) -> None:
    async def _delete() -> None:
        async with generate_async_session() as session:
            user = (await session.exec(select(User).where(User.email == email))).first()
            if not user:
                console_err.print("[bold red]No user found with this email.[/bold red]")
                raise typer.Exit(code=1)
            if user.is_admin:
                console_err.print("[bold red]Cannot delete an admin user.[/bold red]")
                raise typer.Exit(code=1)

            user_sites = (await session.exec(
                select(UserSite).where(UserSite.user_id == user.id)
            )).all()
            for user_site in user_sites:
                await session.delete(user_site)
                console_err.print("[bold yellow]Removed user_site")
            await cache_user.delete(create_redis_client(), user)
            await session.delete(user)
            await session.commit()
            console_err.print("[bold green]User deleted successfully.[/bold green]")

    asyncio.run(_delete())


@app.command(name="export", help="Export all users to a file")
def export(
    format: Annotated[
        export_model.ExportFormat, typer.Option("--format", "-f", help="Export format")
    ] = export_model.ExportFormat.JSON,
    path: Annotated[str | None, typer.Argument(help="Output file path")] = None,
) -> None:
    async def _export() -> None:
        async with generate_async_session() as session:
            await export_model.export_models(
                session, User, path, format.exporter_class
            )
    asyncio.run(_export())


@app.command(name="import", help="Import users from a file")
def import_users(
    format: Annotated[
        import_model.ImportFormat, typer.Option("--format", "-f", help="Import format")
    ] = import_model.ImportFormat.JSON,
    path: Annotated[str | None, typer.Argument(help="Input file path")] = None,
) -> None:
    async def _import() -> None:
        async with generate_async_session() as session:
            await import_model.import_models(
                session, User, path, format.importer_class
            )
    asyncio.run(_import())
