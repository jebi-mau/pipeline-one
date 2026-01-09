#!/usr/bin/env python3
"""Generate a professional corporate-styled PDF reference guide."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from pathlib import Path

# Corporate color scheme
CORP_BLUE = colors.HexColor("#1a365d")
CORP_LIGHT_BLUE = colors.HexColor("#2c5282")
CORP_ACCENT = colors.HexColor("#3182ce")
CORP_GRAY = colors.HexColor("#4a5568")
CORP_LIGHT_GRAY = colors.HexColor("#e2e8f0")
CORP_BG = colors.HexColor("#f7fafc")

OUTPUT_PATH = Path(__file__).parent.parent / "REFERENCE_GUIDE.pdf"


def create_styles():
    """Create professional paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontSize=32,
            leading=40,
            alignment=TA_CENTER,
            textColor=CORP_BLUE,
            spaceAfter=20,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=CORP_GRAY,
            spaceAfter=10,
            fontName="Helvetica",
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeader",
            fontSize=18,
            leading=24,
            textColor=CORP_BLUE,
            spaceBefore=20,
            spaceAfter=12,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubsectionHeader",
            fontSize=13,
            leading=18,
            textColor=CORP_LIGHT_BLUE,
            spaceBefore=14,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CorpBody",
            fontSize=10,
            leading=14,
            textColor=CORP_GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            fontName="Helvetica",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CodeText",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2d3748"),
            fontName="Courier",
            backColor=CORP_LIGHT_GRAY,
            leftIndent=10,
            rightIndent=10,
            spaceBefore=6,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeader",
            fontSize=9,
            leading=12,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            fontSize=9,
            leading=12,
            textColor=CORP_GRAY,
            fontName="Helvetica",
        )
    )

    styles.add(
        ParagraphStyle(
            name="Footer",
            fontSize=8,
            textColor=CORP_GRAY,
            alignment=TA_CENTER,
        )
    )

    return styles


def create_table(data, col_widths=None, header=True):
    """Create a professionally styled table."""
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), CORP_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), CORP_GRAY),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, CORP_LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]

    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(("BACKGROUND", (0, i), (-1, i), CORP_BG))

    table.setStyle(TableStyle(style_commands))
    return table


def add_header_footer(canvas, doc):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(CORP_BLUE)
    canvas.setLineWidth(2)
    canvas.line(40, A4[1] - 40, A4[0] - 40, A4[1] - 40)

    # Footer
    canvas.setFillColor(CORP_GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(40, 30, "SVO2-SAM3 Analyzer Reference Guide")
    canvas.drawRightString(A4[0] - 40, 30, f"Page {doc.page}")

    # Footer line
    canvas.setStrokeColor(CORP_LIGHT_GRAY)
    canvas.setLineWidth(1)
    canvas.line(40, 45, A4[0] - 40, 45)

    canvas.restoreState()


def build_document():
    """Build the complete PDF document."""
    styles = create_styles()
    story = []

    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("SVO2-SAM3 Analyzer", styles["CoverTitle"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Reference Guide", styles["CoverTitle"]))
    story.append(Spacer(1, 0.5 * inch))
    story.append(
        HRFlowable(width="60%", thickness=2, color=CORP_ACCENT, spaceAfter=20)
    )
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "Comprehensive documentation for the SVO2-SAM3 video analysis pipeline",
            styles["CoverSubtitle"],
        )
    )
    story.append(Spacer(1, 1.5 * inch))
    story.append(
        Paragraph(f"Version 1.0 | {datetime.now().strftime('%B %Y')}", styles["CoverSubtitle"])
    )
    story.append(PageBreak())

    # ==================== TABLE OF CONTENTS ====================
    story.append(Paragraph("Table of Contents", styles["SectionHeader"]))
    story.append(Spacer(1, 0.2 * inch))

    toc_items = [
        ("1. Overview", "3"),
        ("2. Processing Pipeline", "3"),
        ("3. API Endpoints", "4"),
        ("4. Job Status Values", "6"),
        ("5. Export Formats", "7"),
        ("6. Configuration Parameters", "8"),
        ("7. Detection Output Formats", "9"),
        ("8. CLI Commands", "10"),
        ("9. Environment Variables", "11"),
        ("10. Error Codes", "12"),
        ("11. Typical Processing Results", "12"),
        ("12. Docker Services", "13"),
        ("13. Frontend Pages", "13"),
    ]

    toc_data = [["Section", "Page"]]
    for item, page in toc_items:
        toc_data.append([item, page])

    story.append(create_table(toc_data, col_widths=[4.5 * inch, 1 * inch]))
    story.append(PageBreak())

    # ==================== SECTION 1: OVERVIEW ====================
    story.append(Paragraph("1. Overview", styles["SectionHeader"]))
    story.append(
        Paragraph(
            "SVO2-SAM3 Analyzer is an end-to-end processing pipeline for analyzing video data from "
            "Stereolabs ZED 2i stereo cameras using SAM 3 (Segment Anything Model 3) for AI-powered "
            "object detection and segmentation.",
            styles["CorpBody"],
        )
    )
    story.append(
        Paragraph(
            "The system provides a complete workflow from raw SVO2 video files to structured output "
            "in industry-standard formats including KITTI, COCO, JSON, and CSV.",
            styles["CorpBody"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    # ==================== SECTION 2: PROCESSING PIPELINE ====================
    story.append(Paragraph("2. Processing Pipeline", styles["SectionHeader"]))
    story.append(
        Paragraph(
            "The system processes data through 5 sequential stages:",
            styles["CorpBody"],
        )
    )

    pipeline_data = [
        ["Stage", "Input", "Output", "Description"],
        ["1. Extraction", "SVO2 file", "Images, depth, point clouds", "Extracts frames from ZED recordings"],
        ["2. Segmentation", "Extracted frames", "2D detections, masks", "Runs SAM 3 object detection"],
        ["3. Reconstruction", "2D detections + depth", "3D bounding boxes", "Projects detections to 3D space"],
        ["4. Tracking", "3D detections", "Object tracks", "Links objects across frames"],
        ["5. Export", "All results", "KITTI/COCO/JSON/CSV", "Generates output files"],
    ]
    story.append(create_table(pipeline_data, col_widths=[1.1 * inch, 1.3 * inch, 1.5 * inch, 2.1 * inch]))
    story.append(PageBreak())

    # ==================== SECTION 3: API ENDPOINTS ====================
    story.append(Paragraph("3. API Endpoints", styles["SectionHeader"]))

    # File Management
    story.append(Paragraph("3.1 File Management (/api/files)", styles["SubsectionHeader"]))
    files_data = [
        ["Endpoint", "Method", "Description", "Expected Result"],
        ["/browse", "GET", "List SVO2 files", "JSON array of file paths"],
        ["/metadata/{path}", "GET", "Get SVO2 file details", "Frame count, resolution, duration"],
        ["/validate", "POST", "Check file integrity", "Validation status and errors"],
    ]
    story.append(create_table(files_data, col_widths=[1.3 * inch, 0.7 * inch, 1.5 * inch, 2.1 * inch]))

    # Job Management
    story.append(Paragraph("3.2 Job Management (/api/jobs)", styles["SubsectionHeader"]))
    jobs_data = [
        ["Endpoint", "Method", "Description", "Expected Result"],
        ["/create", "POST", "Create new job", "Job ID and initial status"],
        ["/", "GET", "List all jobs", "Paginated job list with status"],
        ["/{job_id}", "GET", "Get job details", "Full job info with progress"],
        ["/{job_id}/start", "POST", "Begin processing", "Status changes to processing"],
        ["/{job_id}/pause", "POST", "Pause job", "Status changes to paused"],
        ["/{job_id}/resume", "POST", "Resume paused job", "Continues from pause point"],
        ["/{job_id}/cancel", "POST", "Cancel job", "Status changes to cancelled"],
        ["/{job_id}/results", "GET", "Get processing results", "Detections, tracks, statistics"],
        ["/{job_id}", "DELETE", "Delete job and data", "Job removed from database"],
    ]
    story.append(create_table(jobs_data, col_widths=[1.3 * inch, 0.7 * inch, 1.5 * inch, 2.1 * inch]))

    # Configuration
    story.append(Paragraph("3.3 Configuration (/api/config)", styles["SubsectionHeader"]))
    config_data = [
        ["Endpoint", "Method", "Description", "Expected Result"],
        ["/object-classes", "GET", "List detection classes", "Preset + custom classes"],
        ["/object-classes", "POST", "Add custom class", "New class added"],
        ["/presets", "GET", "List config presets", "Available templates"],
        ["/presets", "POST", "Save preset", "New preset created"],
        ["/model-info", "GET", "SAM3 model details", "Model variant, VRAM info"],
        ["/system", "GET", "System configuration", "Current settings"],
    ]
    story.append(create_table(config_data, col_widths=[1.3 * inch, 0.7 * inch, 1.5 * inch, 2.1 * inch]))
    story.append(PageBreak())

    # Export
    story.append(Paragraph("3.4 Export (/api/export)", styles["SubsectionHeader"]))
    export_data = [
        ["Endpoint", "Method", "Description", "Expected Result"],
        ["/{job_id}", "POST", "Trigger export", "Export task started"],
        ["/{job_id}/status", "GET", "Check export status", "Progress and completion"],
        ["/{job_id}/kitti", "GET", "Download KITTI format", "ZIP file"],
        ["/{job_id}/coco", "GET", "Download COCO format", "JSON file"],
        ["/{job_id}/json", "GET", "Download JSON format", "Full results JSON"],
        ["/{job_id}/csv", "GET", "Download CSV summary", "Statistics spreadsheet"],
        ["/{job_id}/{format}", "DELETE", "Remove export files", "Files deleted"],
    ]
    story.append(create_table(export_data, col_widths=[1.3 * inch, 0.7 * inch, 1.5 * inch, 2.1 * inch]))

    # Health
    story.append(Paragraph("3.5 Health Check", styles["SubsectionHeader"]))
    health_data = [
        ["Endpoint", "Method", "Description", "Expected Result"],
        ["/health", "GET", "System health check", "Status of DB, Redis, GPU"],
        ["/", "GET", "API info", "Version and basic info"],
    ]
    story.append(create_table(health_data, col_widths=[1.3 * inch, 0.7 * inch, 1.5 * inch, 2.1 * inch]))

    # ==================== SECTION 4: JOB STATUS ====================
    story.append(Paragraph("4. Job Status Values", styles["SectionHeader"]))
    status_data = [
        ["Status", "Description"],
        ["pending", "Job created, waiting to start"],
        ["extracting", "Stage 1: Extracting frames from SVO2"],
        ["segmenting", "Stage 2: Running SAM 3 detection"],
        ["reconstructing", "Stage 3: Building 3D bounding boxes"],
        ["tracking", "Stage 4: Linking objects across frames"],
        ["exporting", "Stage 5: Generating output files"],
        ["completed", "All stages finished successfully"],
        ["paused", "Job paused by user"],
        ["cancelled", "Job cancelled by user"],
        ["failed", "Job failed with error"],
    ]
    story.append(create_table(status_data, col_widths=[1.5 * inch, 4.5 * inch]))
    story.append(PageBreak())

    # ==================== SECTION 5: EXPORT FORMATS ====================
    story.append(Paragraph("5. Export Formats", styles["SectionHeader"]))

    story.append(Paragraph("5.1 KITTI Format (ZIP)", styles["SubsectionHeader"]))
    story.append(
        Paragraph(
            "Standard autonomous driving dataset structure:",
            styles["CorpBody"],
        )
    )
    kitti_data = [
        ["Directory", "Contents", "Format"],
        ["image_2/", "Left camera RGB images", "PNG"],
        ["image_3/", "Right camera RGB images", "PNG"],
        ["depth/", "Depth maps", "16-bit PNG"],
        ["velodyne/", "Point clouds", "BIN"],
        ["label_2/", "3D annotations", "TXT"],
        ["oxts/", "IMU/GPS data", "TXT"],
        ["calib/", "Camera calibration", "TXT"],
    ]
    story.append(create_table(kitti_data, col_widths=[1.3 * inch, 2.5 * inch, 1.5 * inch]))

    story.append(Paragraph("5.2 COCO Format (JSON)", styles["SubsectionHeader"]))
    story.append(
        Paragraph(
            "Standard computer vision annotation format containing image metadata, 2D bounding boxes, "
            "segmentation masks (RLE encoded), and category information.",
            styles["CorpBody"],
        )
    )

    story.append(Paragraph("5.3 JSON Format", styles["SubsectionHeader"]))
    story.append(
        Paragraph(
            "Full processing results including complete detection data, 3D bounding boxes, "
            "track assignments, and confidence scores.",
            styles["CorpBody"],
        )
    )

    story.append(Paragraph("5.4 CSV Format", styles["SubsectionHeader"]))
    story.append(
        Paragraph(
            "Summary statistics spreadsheet with frame IDs, timestamps, detection counts, "
            "track counts, per-class counts, and processing times.",
            styles["CorpBody"],
        )
    )

    # ==================== SECTION 6: CONFIGURATION ====================
    story.append(Paragraph("6. Configuration Parameters", styles["SectionHeader"]))

    story.append(Paragraph("6.1 SAM 3 Model Settings", styles["SubsectionHeader"]))
    sam3_data = [
        ["Parameter", "Default", "Description"],
        ["model_variant", "sam3_hiera_large", "Model size (tiny/small/base/large)"],
        ["confidence_threshold", "0.5", "Minimum detection confidence"],
        ["iou_threshold", "0.7", "NMS IoU threshold"],
        ["batch_size", "4", "Frames per batch"],
    ]
    story.append(create_table(sam3_data, col_widths=[1.8 * inch, 1.5 * inch, 2.7 * inch]))

    story.append(Paragraph("6.2 Model VRAM Requirements", styles["SubsectionHeader"]))
    vram_data = [
        ["Variant", "VRAM Required"],
        ["sam3_hiera_tiny", "4 GB"],
        ["sam3_hiera_small", "8 GB"],
        ["sam3_hiera_base", "12 GB"],
        ["sam3_hiera_large", "16 GB"],
    ]
    story.append(create_table(vram_data, col_widths=[2.5 * inch, 2.5 * inch]))
    story.append(PageBreak())

    story.append(Paragraph("6.3 Extraction Settings", styles["SubsectionHeader"]))
    extract_data = [
        ["Parameter", "Options", "Description"],
        ["depth_mode", "NEURAL, ULTRA, QUALITY, PERFORMANCE", "Depth estimation quality"],
        ["frame_skip", "Integer (0+)", "Skip N frames between extractions"],
        ["start_frame", "Integer", "First frame to process"],
        ["end_frame", "Integer", "Last frame to process"],
    ]
    story.append(create_table(extract_data, col_widths=[1.3 * inch, 2.5 * inch, 2.2 * inch]))

    story.append(Paragraph("6.4 Tracking Settings (ByteTrack)", styles["SubsectionHeader"]))
    track_data = [
        ["Parameter", "Default", "Description"],
        ["track_thresh", "0.5", "High confidence detection threshold"],
        ["match_thresh", "0.8", "Track-detection matching threshold"],
        ["track_buffer", "30", "Frames to keep lost tracks"],
    ]
    story.append(create_table(track_data, col_widths=[1.5 * inch, 1.2 * inch, 3.3 * inch]))

    # ==================== SECTION 7: OUTPUT FORMATS ====================
    story.append(Paragraph("7. Detection Output Formats", styles["SectionHeader"]))

    story.append(Paragraph("7.1 2D Detection", styles["SubsectionHeader"]))
    story.append(Paragraph('{"bbox": [x1, y1, x2, y2], "confidence": 0.95, "class_id": 1, "class_name": "person", "mask_path": "path/to/mask.png"}', styles["CodeText"]))

    story.append(Paragraph("7.2 3D Bounding Box", styles["SubsectionHeader"]))
    story.append(Paragraph('{"center": [x, y, z], "dimensions": [length, width, height], "rotation_y": 0.5, "confidence": 0.92}', styles["CodeText"]))

    story.append(Paragraph("7.3 Track", styles["SubsectionHeader"]))
    story.append(Paragraph('{"track_id": 1, "class_name": "car", "start_frame": 10, "end_frame": 150, "trajectory": [[x, y, z], ...]}', styles["CodeText"]))

    # ==================== SECTION 8: CLI COMMANDS ====================
    story.append(Paragraph("8. CLI Commands", styles["SectionHeader"]))

    cli_data = [
        ["Command", "Description", "Expected Result"],
        ["uvicorn backend.app.main:app --host 0.0.0.0 --port 8000", "Start Backend", "API at localhost:8000"],
        ["celery -A worker.celery_app worker --loglevel=info", "Start Worker", "Worker processes tasks"],
        ["cd frontend && npm run dev", "Start Frontend", "UI at localhost:5173"],
        ["alembic upgrade head", "Run Migrations", "Database schema updated"],
        ["python scripts/download_sam3.py", "Download Model", "Weights saved to models/"],
        ["python scripts/verify_gpu.py", "Verify GPU", "CUDA info displayed"],
    ]
    story.append(create_table(cli_data, col_widths=[3.2 * inch, 1.2 * inch, 1.6 * inch]))
    story.append(PageBreak())

    # ==================== SECTION 9: ENVIRONMENT VARIABLES ====================
    story.append(Paragraph("9. Environment Variables", styles["SectionHeader"]))

    env_data = [
        ["Variable", "Description", "Example"],
        ["POSTGRES_HOST", "Database host", "localhost"],
        ["POSTGRES_PORT", "Database port", "5432"],
        ["POSTGRES_DB", "Database name", "svo2_analyzer"],
        ["REDIS_HOST", "Redis host", "localhost"],
        ["REDIS_PORT", "Redis port", "6379"],
        ["DATA_ROOT", "Base data directory", "/data"],
        ["SVO2_DIRECTORY", "Input SVO2 files", "/data/svo2"],
        ["OUTPUT_DIRECTORY", "Processing output", "/data/output"],
        ["SAM3_MODEL_VARIANT", "Model to use", "sam3_hiera_large"],
        ["LOG_LEVEL", "Logging verbosity", "INFO"],
    ]
    story.append(create_table(env_data, col_widths=[1.8 * inch, 2 * inch, 1.8 * inch]))

    # ==================== SECTION 10: ERROR CODES ====================
    story.append(Paragraph("10. Error Codes", styles["SectionHeader"]))

    error_data = [
        ["Code", "Description", "Resolution"],
        ["FILE_NOT_FOUND", "SVO2 file doesn't exist", "Check file path"],
        ["INVALID_SVO2", "Corrupted or unsupported file", "Re-export from ZED software"],
        ["GPU_OUT_OF_MEMORY", "Insufficient VRAM", "Use smaller model or reduce batch"],
        ["ZED_SDK_ERROR", "ZED SDK issue", "Verify SDK installation"],
        ["TASK_TIMEOUT", "Processing exceeded limit", "Split into smaller jobs"],
        ["DATABASE_ERROR", "Database connection failed", "Check PostgreSQL status"],
        ["REDIS_ERROR", "Message broker unavailable", "Check Redis status"],
    ]
    story.append(create_table(error_data, col_widths=[1.5 * inch, 2 * inch, 2.1 * inch]))

    # ==================== SECTION 11: TYPICAL RESULTS ====================
    story.append(Paragraph("11. Typical Processing Results", styles["SectionHeader"]))
    story.append(
        Paragraph(
            "Expected results for a 1000-frame SVO2 recording:",
            styles["CorpBody"],
        )
    )

    results_data = [
        ["Metric", "Typical Value"],
        ["Extraction time", "2-5 minutes"],
        ["Segmentation time", "10-30 minutes (GPU dependent)"],
        ["Reconstruction time", "1-3 minutes"],
        ["Tracking time", "< 1 minute"],
        ["Export time", "1-2 minutes"],
        ["Output size (KITTI ZIP)", "500 MB - 2 GB"],
        ["Detections per frame", "0-50 (scene dependent)"],
        ["Tracks generated", "10-500 (scene dependent)"],
    ]
    story.append(create_table(results_data, col_widths=[2.5 * inch, 3 * inch]))
    story.append(PageBreak())

    # ==================== SECTION 12: DOCKER ====================
    story.append(Paragraph("12. Docker Services", styles["SectionHeader"]))

    docker_data = [
        ["Service", "Port", "Description"],
        ["postgres", "5432", "PostgreSQL database"],
        ["redis", "6379", "Message broker"],
        ["redis-commander", "8081", "Redis web UI (debug)"],
        ["pgadmin", "5050", "Database admin UI (debug)"],
    ]
    story.append(create_table(docker_data, col_widths=[1.8 * inch, 1 * inch, 3 * inch]))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Start services:", styles["CorpBody"]))
    story.append(Paragraph("docker-compose up -d", styles["CodeText"]))
    story.append(Paragraph("Start with debug tools:", styles["CorpBody"]))
    story.append(Paragraph("docker-compose --profile debug up -d", styles["CodeText"]))

    # ==================== SECTION 13: FRONTEND ====================
    story.append(Paragraph("13. Frontend Pages", styles["SectionHeader"]))

    frontend_data = [
        ["Page", "Route", "Description"],
        ["Home", "/", "Feature overview and quick start"],
        ["Jobs", "/jobs", "Job list and management"],
        ["Job Detail", "/jobs/:id", "Job progress and results"],
        ["Settings", "/settings", "System configuration"],
    ]
    story.append(create_table(frontend_data, col_widths=[1.5 * inch, 1.5 * inch, 3 * inch]))

    story.append(Spacer(1, 0.5 * inch))
    story.append(
        HRFlowable(width="100%", thickness=1, color=CORP_LIGHT_GRAY, spaceAfter=10)
    )
    story.append(
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | SVO2-SAM3 Analyzer v1.0",
            styles["Footer"],
        )
    )

    return story


def main():
    """Generate the PDF document."""
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=60,
    )

    story = build_document()
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
