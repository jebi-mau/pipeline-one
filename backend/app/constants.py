"""Application constants."""

from typing import Final

# Default pipeline stages (in execution order)
DEFAULT_PIPELINE_STAGES: Final[list[str]] = [
    "extraction",
    "segmentation",
    "reconstruction",
    "tracking",
]

# Stage number mapping
STAGE_NUMBERS: Final[dict[str, int]] = {
    "extraction": 1,
    "segmentation": 2,
    "reconstruction": 3,
    "tracking": 4,
}

# Stage weights for progress calculation (must sum to 1.0)
STAGE_WEIGHTS: Final[dict[str, float]] = {
    "extraction": 0.25,
    "segmentation": 0.50,
    "reconstruction": 0.15,
    "tracking": 0.10,
}
