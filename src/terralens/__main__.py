"""TerraLens CLI — entrypoint."""

import signal
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TimeRemainingColumn,
)

app = typer.Typer(
    name="terralens",
    help="Interaktywny 3D eksplorator zmian powierzchni Ziemi.",
    no_args_is_help=True,
)
console = Console()

_INTERRUPTED = False


def _handle_sigint(sig, frame):  # noqa: ANN001
    global _INTERRUPTED
    _INTERRUPTED = True
    console.print("\n[yellow]Przerwano — cache.db nie jest uszkodzony.[/yellow]")


signal.signal(signal.SIGINT, _handle_sigint)


def _iter_months(start: date, end: date):
    """Generator dat pierwszego dnia każdego miesiąca w zakresie [start, end]."""
    cur = start.replace(day=1)
    while cur <= end:
        yield cur.strftime("%Y-%m-%d")
        # Przejdź do następnego miesiąca
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


@app.command()
def fetch(
    region: str = typer.Option("amazonia", help="Region (amazonia/dubai/arctic)."),
    start_date: str = typer.Option("2015-01-01", help="Data początkowa YYYY-MM-DD."),
    end_date: str = typer.Option("2024-12-31", help="Data końcowa YYYY-MM-DD."),
    layer: str = typer.Option("MODIS_NDVI", help="Warstwa (HLS_RGB/MODIS_NDVI)."),
    zoom: int = typer.Option(6, help="Poziom zoomu WMTS."),
    force: bool = typer.Option(False, help="Wymuś pobranie mimo ważnego cache."),
) -> None:
    """Pobiera tile'y NASA GIBS dla regionu i zakresu dat (monthly)."""
    import requests

    from terralens.fetchers.gibs import fetch_tile
    from terralens.fetchers.regions import region_tiles

    try:
        tiles = region_tiles(region, zoom)
        dates = list(_iter_months(date.fromisoformat(start_date), date.fromisoformat(end_date)))
    except ValueError as exc:
        console.print(f"[red]Błąd:[/red] {exc}")
        raise typer.Exit(1)

    total = len(tiles) * len(dates)
    console.print(
        f"[cyan]Region:[/cyan] {region} | "
        f"[cyan]Warstwa:[/cyan] {layer} | "
        f"[cyan]Tile'ów:[/cyan] {len(tiles)} × {len(dates)} dat = {total}"
    )

    sess = requests.Session()
    ok = err = skipped = 0

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Pobieranie...", total=total)

        for d in dates:
            if _INTERRUPTED:
                break
            for z, x, y in tiles:
                if _INTERRUPTED:
                    break
                try:
                    fetch_tile(layer, d, z, x, y, session=sess, force=force)
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    err += 1
                    console.log(f"[red]BŁĄD[/red] {layer}/{d}/{z}/{x}/{y}: {exc}")
                finally:
                    progress.advance(task)

    console.print(f"[green]OK:[/green] {ok}  [red]Błędy:[/red] {err}  Pominięto (cache): {skipped}")
    if err:
        raise typer.Exit(1)


@app.command()
def process(
    region: str = typer.Option("amazonia", help="Region do przetworzenia."),
    force: bool = typer.Option(False, help="Wymuś ponowne przetworzenie."),
) -> None:
    """Przetwarza pobrane dane (Satlas ESRGAN SR, SSIM change detection, NDVI diff)."""
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def export(
    region: str = typer.Option("amazonia", help="Region (amazonia/dubai/arctic)."),
    output: str = typer.Option("data/export", help="Katalog wyjściowy PMTiles."),
    layer: str = typer.Option("HLS_RGB", help="Warstwa źródłowa (HLS_RGB/MODIS_NDVI)."),
) -> None:
    """Eksportuje pobrane tile'y do pliku PMTiles (WebP, quality=85)."""
    from datetime import datetime, timezone

    from terralens.config import get_config
    from terralens.export.pmtiles import build_pmtiles
    from terralens.fetchers.regions import REGIONS

    cfg = get_config()

    if region not in REGIONS:
        console.print(f"[red]Nieznany region:[/red] {region!r}. Dostępne: {list(REGIONS)}")
        raise typer.Exit(1)

    tile_dir = cfg.data_dir / "tiles" / layer
    if not tile_dir.exists():
        console.print(f"[red]Brak tile'ów w:[/red] {tile_dir} (uruchom najpierw: terralens fetch)")
        raise typer.Exit(1)

    bounds = REGIONS[region]
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(output) / f"{region}_v{timestamp}.pmtiles"

    metadata = {
        "bounds": bounds,
        "source_layer": layer,
        "region": region,
        "tile_size": cfg.tile_size,
        "creation_date": datetime.now(tz=timezone.utc).isoformat(),
    }

    console.print(
        f"[cyan]Eksport:[/cyan] {region} | [cyan]Warstwa:[/cyan] {layer} | "
        f"[cyan]Źródło:[/cyan] {tile_dir}"
    )

    from terralens.export.manifest import generate_manifest, save_manifest

    try:
        result = build_pmtiles(tile_dir, output_path, metadata)
        size_mb = result.stat().st_size / 1_048_576
        console.print(f"[green]PMTiles zapisano:[/green] {result} ({size_mb:.1f} MB)")

        manifest = generate_manifest(
            regions=list(REGIONS),
            export_dir=Path(output),
            db_path=cfg.cache_db,
            processed_dir=cfg.data_dir / "processed",
        )
        manifest_path = Path(output) / "manifest.json"
        save_manifest(manifest, manifest_path)
        console.print(f"[green]Manifest zapisano:[/green] {manifest_path}")
        console.print(f"[cyan]Sprawdź:[/cyan] pmtiles show {result}")
    except ValueError as exc:
        console.print(f"[red]Błąd:[/red] {exc}")
        raise typer.Exit(1)


@app.command()
def deploy(
    dry_run: bool = typer.Option(False, help="Symulacja bez uploadu do R2."),
) -> None:
    """Wgrywa PMTiles na Cloudflare R2 i aktualizuje manifest.json."""
    console.print("[yellow]Not implemented yet[/yellow]")


if __name__ == "__main__":
    app()
