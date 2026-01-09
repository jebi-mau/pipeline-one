#!/usr/bin/env python3
"""Download SAM 3 model weights from Hugging Face."""

import argparse
import sys
from pathlib import Path

from rich.console import Console

console = Console()


def get_default_model_dir() -> Path:
    """Get default model directory."""
    project_dir = Path(__file__).parent.parent
    data_models = project_dir / "data" / "models" / "sam3"
    if data_models.parent.exists():
        return data_models
    return Path.home() / ".cache" / "jebi" / "models" / "sam3"


def download_from_huggingface(output_dir: Path, force: bool = False) -> bool:
    """Download SAM 3 from Hugging Face."""
    try:
        from huggingface_hub import snapshot_download, whoami
    except ImportError:
        console.print("[red]huggingface_hub not installed. Run: pip install huggingface_hub[/red]")
        return False

    # Check authentication
    try:
        user = whoami()
        console.print(f"[green]Authenticated as: {user['name']}[/green]")
    except Exception:
        console.print("[yellow]Not authenticated with Hugging Face.[/yellow]")
        console.print("Run: huggingface-cli login")
        console.print("Or set HF_TOKEN environment variable")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Downloading SAM 3 from Hugging Face...[/bold]")
    console.print(f"Repository: facebook/sam3")
    console.print(f"Output: {output_dir}\n")

    try:
        snapshot_download(
            repo_id="facebook/sam3",
            local_dir=output_dir,
            force_download=force,
        )
        console.print(f"\n[green]Successfully downloaded SAM 3 to {output_dir}[/green]")
        return True
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "gated" in error_msg.lower():
            console.print("\n[red]Access denied to SAM 3 repository.[/red]")
            console.print("\n[yellow]SAM 3 is a gated model. To get access:[/yellow]")
            console.print("1. Visit: https://huggingface.co/facebook/sam3")
            console.print("2. Click 'Access repository' and accept the terms")
            console.print("3. Wait for approval (usually instant)")
            console.print("4. Re-run this script")
        else:
            console.print(f"[red]Download failed: {e}[/red]")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download SAM 3 model weights from Hugging Face")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for model weights",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist",
    )

    args = parser.parse_args()

    output_dir = args.output_dir or get_default_model_dir()

    console.print("\n[bold]SAM 3 Model Download[/bold]")
    console.print("=" * 40)
    console.print("\nSAM 3 (Segment Anything with Concepts)")
    console.print("- 848M parameters")
    console.print("- Native text prompt support")
    console.print("- 270K+ open-vocabulary concepts")
    console.print("- Requires Hugging Face authentication")
    console.print()

    if download_from_huggingface(output_dir, args.force):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
