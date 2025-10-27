"""Command-line interface for the Gmail digest tool."""

from __future__ import annotations

from datetime import UTC, datetime

import typer

from gmail_digest_tool.config.settings import get_settings
from gmail_digest_tool.main import run_digest

app = typer.Typer(help="CLI entrypoint for the Gmail digest generator.")


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse a datetime string into an aware datetime."""
    if value is None:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise typer.BadParameter(f"Invalid datetime value: {value}") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def generate(
    unread: bool | None = typer.Option(
        None,
        "--unread/--all",
        help="Filter only unread emails when set. Defaults to configuration value.",
        show_default=False,
    ),
    from_datetime: str | None = typer.Option(
        None,
        "--from-datetime",
        help="Start of time range (ISO 8601). Defaults to 24h lookback.",
    ),
    to_datetime: str | None = typer.Option(
        None,
        "--to-datetime",
        help="End of time range (ISO 8601). Defaults to 24h lookback.",
    ),
) -> None:
    """Generate a Gmail digest."""
    settings = get_settings()
    unread_only = unread if unread is not None else settings.default_unread

    parsed_from = _parse_datetime(from_datetime)
    parsed_to = _parse_datetime(to_datetime)

    output_path = run_digest(
        unread_only=unread_only,
        from_datetime=parsed_from,
        to_datetime=parsed_to,
        settings=settings,
    )

    typer.echo(f"Digest written to {output_path}")


app.command()(generate)


def run() -> None:
    """Invoke the Typer application."""
    app()
