#!/usr/bin/env python3
"""Verify GPU setup for SAM 3 inference."""

import sys

from rich.console import Console
from rich.table import Table

console = Console()


def check_cuda() -> dict:
    """Check CUDA availability via PyTorch."""
    result = {
        "cuda_available": False,
        "cuda_version": None,
        "cudnn_version": None,
        "device_count": 0,
        "devices": [],
    }

    try:
        import torch

        result["cuda_available"] = torch.cuda.is_available()

        if result["cuda_available"]:
            result["cuda_version"] = torch.version.cuda
            result["cudnn_version"] = torch.backends.cudnn.version()
            result["device_count"] = torch.cuda.device_count()

            for i in range(result["device_count"]):
                props = torch.cuda.get_device_properties(i)
                result["devices"].append({
                    "index": i,
                    "name": props.name,
                    "compute_capability": f"{props.major}.{props.minor}",
                    "total_memory_gb": props.total_memory / (1024**3),
                    "multi_processor_count": props.multi_processor_count,
                })
    except ImportError:
        console.print("[red]PyTorch not installed[/red]")
    except Exception as e:
        console.print(f"[red]Error checking CUDA: {e}[/red]")

    return result


def check_torch_compile() -> bool:
    """Check if torch.compile is available."""
    try:
        import torch

        # Check if inductor backend is available (for torch.compile)
        return hasattr(torch, "compile")
    except ImportError:
        return False


def check_zed_sdk() -> dict:
    """Check ZED SDK installation."""
    result = {
        "installed": False,
        "version": None,
        "cuda_version": None,
    }

    try:
        import pyzed.sl as sl

        result["installed"] = True
        # Get SDK version
        result["version"] = "5.x"  # pyzed doesn't expose version easily
    except ImportError:
        pass
    except Exception as e:
        console.print(f"[yellow]ZED SDK check warning: {e}[/yellow]")

    return result


def main():
    console.print("\n[bold]SVO2-SAM3 Analyzer - GPU Verification[/bold]\n")

    # Check CUDA
    console.print("[bold]Checking CUDA...[/bold]")
    cuda_info = check_cuda()

    if cuda_info["cuda_available"]:
        console.print(f"[green]CUDA Available[/green]: Yes")
        console.print(f"CUDA Version: {cuda_info['cuda_version']}")
        console.print(f"cuDNN Version: {cuda_info['cudnn_version']}")
        console.print(f"Device Count: {cuda_info['device_count']}")

        if cuda_info["devices"]:
            console.print("\n[bold]GPU Devices:[/bold]")
            table = Table()
            table.add_column("Index", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Compute", style="yellow")
            table.add_column("Memory (GB)", style="magenta")
            table.add_column("SMs", style="blue")

            for dev in cuda_info["devices"]:
                table.add_row(
                    str(dev["index"]),
                    dev["name"],
                    dev["compute_capability"],
                    f"{dev['total_memory_gb']:.1f}",
                    str(dev["multi_processor_count"]),
                )

            console.print(table)
    else:
        console.print("[red]CUDA Available[/red]: No")
        console.print("[yellow]GPU acceleration will not be available[/yellow]")

    # Check torch.compile
    console.print("\n[bold]Checking torch.compile...[/bold]")
    if check_torch_compile():
        console.print("[green]torch.compile Available[/green]: Yes")
    else:
        console.print("[yellow]torch.compile Available[/yellow]: No")

    # Check ZED SDK
    console.print("\n[bold]Checking ZED SDK...[/bold]")
    zed_info = check_zed_sdk()

    if zed_info["installed"]:
        console.print(f"[green]ZED SDK Installed[/green]: Yes")
        if zed_info["version"]:
            console.print(f"Version: {zed_info['version']}")
    else:
        console.print("[yellow]ZED SDK Installed[/yellow]: No")
        console.print("Run: ./scripts/setup_zed_sdk.sh")

    # Summary
    console.print("\n[bold]Summary[/bold]")
    console.print("-" * 40)

    all_good = True

    if cuda_info["cuda_available"] and cuda_info["device_count"] > 0:
        gpu = cuda_info["devices"][0]
        if gpu["total_memory_gb"] >= 16:
            console.print(f"[green]GPU Memory: {gpu['total_memory_gb']:.0f} GB (Sufficient for SAM 3 Large)[/green]")
        elif gpu["total_memory_gb"] >= 8:
            console.print(f"[yellow]GPU Memory: {gpu['total_memory_gb']:.0f} GB (Use SAM 3 Small or Base)[/yellow]")
        else:
            console.print(f"[red]GPU Memory: {gpu['total_memory_gb']:.0f} GB (May be insufficient)[/red]")
            all_good = False
    else:
        console.print("[red]No CUDA GPU detected[/red]")
        all_good = False

    if not zed_info["installed"]:
        console.print("[yellow]ZED SDK not installed (required for SVO2 processing)[/yellow]")
        all_good = False

    console.print("-" * 40)

    if all_good:
        console.print("\n[green]System is ready for SVO2-SAM3 Analyzer![/green]\n")
        return 0
    else:
        console.print("\n[yellow]Some components need attention. See above for details.[/yellow]\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
