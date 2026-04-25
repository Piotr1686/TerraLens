"""TerraLens CLI — entrypoint."""

import typer
from rich.console import Console

app = typer.Typer(
    name="terralens",
    help="Interaktywny 3D eksplorator zmian powierzchni Ziemi.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def fetch(
    region: str = typer.Option("amazonia", help="Region do pobrania (amazonia/dubai/arctic)."),
    year_start: int = typer.Option(2015, help="Rok początkowy."),
    year_end: int = typer.Option(2024, help="Rok końcowy."),
) -> None:
    """Pobiera dane NASA (GIBS HLS RGB, MODIS NDVI, SRTM DEM) dla podanego regionu."""
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def process(
    region: str = typer.Option("amazonia", help="Region do przetworzenia."),
    force: bool = typer.Option(False, help="Wymuś ponowne przetworzenie."),
) -> None:
    """Przetwarza pobrane dane (Satlas ESRGAN SR, SSIM change detection, NDVI diff)."""
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def export(
    region: str = typer.Option("amazonia", help="Region do eksportu."),
    output: str = typer.Option("data/export", help="Katalog wyjściowy PMTiles."),
) -> None:
    """Eksportuje przetworzone dane do formatu PMTiles."""
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def deploy(
    dry_run: bool = typer.Option(False, help="Symulacja bez uploadu do R2."),
) -> None:
    """Wgrywa PMTiles na Cloudflare R2 i aktualizuje manifest.json."""
    console.print("[yellow]Not implemented yet[/yellow]")


if __name__ == "__main__":
    app()
