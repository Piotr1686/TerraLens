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
    zoom: str = typer.Option(
        "6", help="Poziomy zoomu WMTS, lista rozdzielona przecinkami (np. '6,7,8')."
    ),
    force: bool = typer.Option(False, help="Wymuś pobranie mimo ważnego cache."),
) -> None:
    """Pobiera tile'y NASA GIBS dla regionu i zakresu dat (monthly)."""
    import requests
    import urllib3
    import urllib3.exceptions

    from terralens.fetchers.gibs import fetch_tile
    from terralens.fetchers.regions import region_tiles

    # NASA GIBS używa intermediate certa którego certifi nie zawsze rozpoznaje na Windows
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        zoom_levels = [int(z.strip()) for z in zoom.split(",")]
        tiles: list[tuple[int, int, int]] = []
        for z_lvl in zoom_levels:
            tiles.extend(region_tiles(region, z_lvl))
        dates = list(_iter_months(date.fromisoformat(start_date), date.fromisoformat(end_date)))
    except ValueError as exc:
        console.print(f"[red]Błąd:[/red] {exc}")
        raise typer.Exit(1)

    total = len(tiles) * len(dates)
    zoom_label = zoom if "," in zoom else zoom
    console.print(
        f"[cyan]Region:[/cyan] {region} | "
        f"[cyan]Warstwa:[/cyan] {layer} | "
        f"[cyan]Zoom:[/cyan] {zoom_label} | "
        f"[cyan]Tile'ów:[/cyan] {len(tiles)} × {len(dates)} dat = {total}"
    )

    sess = requests.Session()
    sess.verify = False
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
    layer: str = typer.Option("HLS_RGB", help="Warstwa źródłowa (HLS_RGB/MODIS_NDVI)."),
    zoom: str = typer.Option(
        "6", help="Poziomy zoomu (filtr tile'ów po bbox regionu), np. '6,7,8'."
    ),
    force: bool = typer.Option(False, help="Wymuś ponowne przetworzenie."),
) -> None:
    """Uruchamia Real-ESRGAN 4× SR na pobranych tile'ach -> {layer}_SR/."""
    import gc

    import numpy as np
    import torch
    from PIL import Image

    from terralens.config import get_config
    from terralens.engines.realesrgan import get_esrgan
    from terralens.export.pmtiles import scan_tiles
    from terralens.fetchers.regions import region_tiles

    cfg = get_config()
    src_dir = cfg.data_dir / "tiles" / layer
    dst_dir = cfg.data_dir / "tiles" / f"{layer}_SR"

    if not src_dir.exists():
        console.print(f"[red]Brak tile'ów w:[/red] {src_dir} (uruchom: terralens fetch)")
        raise typer.Exit(1)

    try:
        zoom_levels = [int(z_str.strip()) for z_str in zoom.split(",")]
        region_set = {
            (z_lvl, x, y) for z_lvl in zoom_levels for _, x, y in region_tiles(region, z_lvl)
        }
    except ValueError as exc:
        console.print(f"[red]Błąd:[/red] {exc}")
        raise typer.Exit(1)

    all_tiles = scan_tiles(src_dir)
    tiles = [(z, x, y, p) for z, x, y, p in all_tiles if (z, x, y) in region_set]

    if not tiles:
        console.print(
            f"[yellow]Brak tile'ów dla regionu {region!r} zoom={zoom} w:[/yellow] {src_dir}"
        )
        raise typer.Exit(1)

    console.print(
        f"[cyan]ESRGAN 4×:[/cyan] {len(tiles)} tile'ów | "
        f"[cyan]Źródło:[/cyan] {layer} → [cyan]Cel:[/cyan] {layer}_SR"
    )

    esrgan = get_esrgan()
    esrgan.load()

    ok = skipped = err = 0

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("ESRGAN SR...", total=len(tiles))

        for i, (z, x, y, src_path) in enumerate(tiles):
            if _INTERRUPTED:
                break

            rel = src_path.relative_to(src_dir)
            dst_path = (dst_dir / rel).with_suffix(".webp")

            if not force and dst_path.exists():
                skipped += 1
                progress.advance(task)
                continue

            try:
                arr = np.array(Image.open(src_path).convert("RGB"), dtype=np.float32) / 255.0
                sr = esrgan.upscale(arr)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray((sr * 255).clip(0, 255).astype(np.uint8)).save(
                    dst_path, format="WEBP", quality=85, method=4
                )
                ok += 1
            except Exception as exc:  # noqa: BLE001
                err += 1
                console.log(f"[red]BŁĄD[/red] {src_path}: {exc}")
            finally:
                progress.advance(task)

            if (i + 1) % cfg.empty_cache_every_n_tiles == 0:
                torch.cuda.empty_cache()
                gc.collect()

    esrgan.unload()
    console.print(
        f"[green]SR:[/green] {ok}  [yellow]Pominięto:[/yellow] {skipped}  [red]Błędy:[/red] {err}"
    )
    if err:
        raise typer.Exit(1)


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
    region: str = typer.Option("amazonia", help="Region (amazonia/dubai/arctic)."),
    export_dir: str = typer.Option("data/export", help="Katalog z plikami PMTiles."),
    dry_run: bool = typer.Option(False, help="Symulacja bez uploadu do HF."),
) -> None:
    """Wgrywa PMTiles + manifest.json na Hugging Face Datasets (CDN)."""
    from terralens.export.deploy import _load_hf_config, collect_deploy_files, deploy_files

    try:
        token, repo_id, public_url_base = _load_hf_config()
    except OSError as exc:
        console.print(f"[red]Błąd konfiguracji:[/red] {exc}")
        console.print("Dodaj HF_TOKEN i HF_REPO_ID do pliku .env")
        raise typer.Exit(1)

    files = collect_deploy_files(Path(export_dir), region)
    if not files:
        console.print(f"[yellow]Brak plików do deploy w:[/yellow] {export_dir}")
        raise typer.Exit(1)

    console.print(
        f"[cyan]Deploy:[/cyan] {region} -> [cyan]{repo_id}[/cyan]"
        + (" [yellow](dry-run)[/yellow]" if dry_run else "")
    )
    for f in files:
        console.print(f"  • {f.name}")

    uploaded: list[str] = []

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Uploading..." if not dry_run else "Dry-run...", total=len(files))

        def _tick(filename: str) -> None:
            uploaded.append(filename)
            progress.advance(task)

        result = deploy_files(
            files,
            token=token,
            repo_id=repo_id,
            public_url_base=public_url_base,
            dry_run=dry_run,
            on_progress=_tick,
        )

    console.print(
        f"[green]{'Dry-run' if dry_run else 'Upload'} zakończony:[/green] {len(result)} plików"
    )
    for filename, url in result.items():
        console.print(f"  [cyan]{url}[/cyan]")

    if not dry_run:
        console.print(f"\n[green]Manifest publiczny:[/green] {public_url_base}/manifest.json")


@app.command(name="deploy-changes")
def deploy_changes(
    processed_dir: str = typer.Option("data/processed", help="Katalog z changes.json."),
    dry_run: bool = typer.Option(False, help="Symulacja bez uploadu do HF."),
) -> None:
    """Wgrywa changes.json na Hugging Face Datasets (CDN)."""
    from terralens.export.deploy import _load_hf_config, deploy_files

    json_path = Path(processed_dir) / "changes.json"
    if not json_path.exists():
        console.print(f"[red]Brak pliku:[/red] {json_path}")
        raise typer.Exit(1)

    try:
        token, repo_id, public_url_base = _load_hf_config()
    except OSError as exc:
        console.print(f"[red]Błąd konfiguracji:[/red] {exc}")
        console.print("Dodaj HF_TOKEN i HF_REPO_ID do pliku .env")
        raise typer.Exit(1)

    console.print(
        f"[cyan]Deploy changes.json:[/cyan] {json_path} -> [cyan]{repo_id}[/cyan]"
        + (" [yellow](dry-run)[/yellow]" if dry_run else "")
    )

    result = deploy_files(
        [json_path],
        token=token,
        repo_id=repo_id,
        public_url_base=public_url_base,
        dry_run=dry_run,
    )

    console.print(f"[green]{'Dry-run' if dry_run else 'Upload'} zakończony[/green]")
    for filename, url in result.items():
        console.print(f"  [cyan]{url}[/cyan]")


@app.command(name="deploy-heatmaps")
def deploy_heatmaps(
    processed_dir: str = typer.Option("data/processed", help="Katalog z {region}/heatmap."),
    dry_run: bool = typer.Option(False, help="Symulacja bez uploadu do HF."),
) -> None:
    """Wgrywa heatmapy na HF: {region}_ssim_heatmap i {region}_ndvi_heatmap/{z}/{x}/{y}.png."""
    from terralens.export.deploy import _load_hf_config, deploy_folder

    token, repo_id, public_url_base = _load_hf_config()
    regions = ["amazonia", "dubai", "arctic"]
    # (lokalny podkatalog w {region}/, sufiks repo HF)
    metrics = [("heatmap", "ssim_heatmap"), ("ndvi_heatmap", "ndvi_heatmap")]

    found = False
    for region in regions:
        for subdir, suffix in metrics:
            local = Path(processed_dir) / region / subdir
            if not local.exists() or not any(local.rglob("*.png")):
                console.print(f"[yellow]Brak {suffix} dla {region} ({local}) — pomijam[/yellow]")
                continue
            found = True
            console.print(
                f"[cyan]Deploy {suffix} {region}:[/cyan] {local} -> "
                f"[cyan]{repo_id}/{region}_{suffix}[/cyan]"
                + (" [yellow](dry-run)[/yellow]" if dry_run else "")
            )
            base = deploy_folder(
                local,
                f"{region}_{suffix}",
                token=token,
                repo_id=repo_id,
                public_url_base=public_url_base,
                dry_run=dry_run,
            )
            console.print(f"  [cyan]{base}/{{z}}/{{x}}/{{y}}.png[/cyan]")

    if not found:
        console.print(
            "[red]Brak heatmap do deployu — uruchom najpierw scripts/build_heatmaps.py[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[green]{'Dry-run' if dry_run else 'Upload'} zakończony[/green]")


if __name__ == "__main__":
    app()
