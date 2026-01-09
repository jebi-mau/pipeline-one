"""Custom exceptions for the application."""

from typing import Any


class SVO2AnalyzerError(Exception):
    """Base exception for SVO2 Analyzer."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SVO2FileError(SVO2AnalyzerError):
    """Exception for SVO2 file operations."""

    pass


class SVO2ReadError(SVO2FileError):
    """Exception for SVO2 file read errors."""

    pass


class SVO2ExtractionError(SVO2FileError):
    """Exception for SVO2 data extraction errors."""

    pass


class ProcessingError(SVO2AnalyzerError):
    """Exception for processing pipeline errors."""

    pass


class SAM3Error(ProcessingError):
    """Exception for SAM 3 model errors."""

    pass


class SAM3ModelLoadError(SAM3Error):
    """Exception for SAM 3 model loading errors."""

    pass


class SAM3InferenceError(SAM3Error):
    """Exception for SAM 3 inference errors."""

    pass


class ReconstructionError(ProcessingError):
    """Exception for 3D reconstruction errors."""

    pass


class TrackingError(ProcessingError):
    """Exception for object tracking errors."""

    pass


class ExportError(SVO2AnalyzerError):
    """Exception for export operations."""

    pass


class JobError(SVO2AnalyzerError):
    """Exception for job management errors."""

    pass


class JobNotFoundError(JobError):
    """Exception when job is not found."""

    pass


class JobStateError(JobError):
    """Exception for invalid job state transitions."""

    pass


class ConfigurationError(SVO2AnalyzerError):
    """Exception for configuration errors."""

    pass


class DatabaseError(SVO2AnalyzerError):
    """Exception for database errors."""

    pass
