"""``signalguard-api`` console script. Thin uvicorn launcher."""

from __future__ import annotations

import click
import uvicorn


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
@click.option("--reload", is_flag=True, default=False, help="Reload on code change.")
@click.option(
    "--log-level",
    default="info",
    show_default=True,
    type=click.Choice(["critical", "error", "warning", "info", "debug", "trace"]),
)
def main(host: str, port: int, reload: bool, log_level: str) -> None:
    """Run the signalguard FastAPI app under uvicorn."""
    uvicorn.run(
        "signalguard_api.main:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
