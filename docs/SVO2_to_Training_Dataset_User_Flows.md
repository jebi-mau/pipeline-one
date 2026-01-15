# SVO2 to Training Dataset: Complete User Flow Documentation

**Document Version:** 1.0
**Last Updated:** January 2026
**System:** SVO2-SAM3 Analyzer Pipeline

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Phase 1: SVO2 File Input](#phase-1-svo2-file-input)
4. [Phase 2: Job Configuration](#phase-2-job-configuration)
5. [Phase 3: Pipeline Execution](#phase-3-pipeline-execution)
6. [Phase 4: Review and Curation](#phase-4-review-and-curation)
7. [Phase 5: Training Dataset Export](#phase-5-training-dataset-export)
8. [Flow Variations](#flow-variations)
9. [Data Model Reference](#data-model-reference)
10. [API Reference](#api-reference)
11. [File Reference](#file-reference)

---

## Executive Summary

This document provides a comprehensive mapping of all user flows from SVO2 file input through Training Dataset creation in the SVO2-SAM3 Analyzer Pipeline. The system processes ZED stereo camera recordings (SVO2 format) through a multi-stage pipeline to produce annotated training datasets suitable for machine learning model development.

**Key Capabilities:**
- Automated object detection and segmentation using SAM3
- 3D bounding box reconstruction from stereo depth
- Multi-object tracking across video sequences
- Flexible data curation and filtering
- Export to industry-standard formats (KITTI, COCO)

---

## System Overview

```
                                    SYSTEM ARCHITECTURE

    ┌──────────────────────────────────────────────────────────────────────────┐
    │                                                                          │
    │   INPUT                PROCESSING                OUTPUT                  │
    │                                                                          │
    │   ┌─────────┐         ┌─────────────┐         ┌─────────────────┐       │
    │   │  SVO2   │────────▶│   4-Stage   │────────▶│ Training        │       │
    │   │  Files  │         │   Pipeline  │         │ Dataset         │       │
    │   └─────────┘         └─────────────┘         │ (KITTI/COCO)    │       │
    │                              │                 └─────────────────┘       │
    │                              │                                           │
    │                              ▼                                           │
    │                       ┌─────────────┐                                    │
    │                       │   Review    │                                    │
    │                       │   & Filter  │                                    │
    │                       └─────────────┘                                    │
    │                                                                          │
    └──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: SVO2 File Input

The system supports two primary methods for ingesting SVO2 files.

### Method A: Direct File Selection

Users browse the filesystem and select individual SVO2 files directly.

| Step | Action | Endpoint |
|------|--------|----------|
| 1 | Browse directory | `GET /files/browse` |
| 2 | Select SVO2 files | UI selection |
| 3 | Retrieve frame count | `GET /files/frame-count` |
| 4 | Validate file integrity | `POST /files/validate` |

**Characteristics:**
- Fastest path to processing
- No persistent dataset record
- Limited lineage tracking

### Method B: Dataset-Based Import

Users create a Dataset record and scan a folder for SVO2 files.

| Step | Action | Endpoint |
|------|--------|----------|
| 1 | Create dataset | `POST /datasets` |
| 2 | Scan source folder | `POST /datasets/{id}/scan` |
| 3 | Extract metadata | Automatic |
| 4 | Prepare files | `POST /datasets/{id}/prepare` |
| 5 | Copy/rename files | Automatic |

**Characteristics:**
- Full provenance tracking
- Camera metadata extraction
- Organized output structure
- Recommended for production workflows

### SVO2 File Processing

The system uses the ZED SDK (pyzed) to read SVO2 files:

| Data Type | Description |
|-----------|-------------|
| Left RGB | Primary camera image |
| Right RGB | Stereo pair image |
| Depth Map | Computed depth values |
| Point Cloud | 3D point representation |
| IMU Data | Accelerometer/gyroscope readings |

---

## Phase 2: Job Configuration

Jobs encapsulate all processing parameters and track execution state.

### Job Creation Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_paths` | string[] | Direct SVO2 file paths |
| `dataset_id` | UUID | Reference to Dataset (enables lineage) |
| `stages_to_run` | string[] | Pipeline stages to execute |
| `sam3_variant` | string | Model: tiny, small, base, large |
| `confidence_threshold` | float | Detection confidence cutoff |
| `batch_size` | int | Frames per batch |
| `frame_skip` | int | Process every Nth frame |
| `enable_diversity_filter` | bool | Filter similar frames during extraction |
| `similarity_threshold` | float | Perceptual hash distance threshold |
| `motion_threshold` | float | Minimum inter-frame motion |
| `object_class_ids` | int[] | Object classes to detect |

### Stage Selection

Users may select any combination of stages. Dependencies are automatically resolved.

| Stage | Weight | Dependencies |
|-------|--------|--------------|
| Extraction | 25% | None |
| Segmentation | 50% | Extraction |
| Reconstruction | 15% | Segmentation |
| Tracking | 10% | Reconstruction |

**Dependency Resolution Example:**
- User selects: `[tracking]`
- System runs: `[extraction, segmentation, reconstruction, tracking]`

---

## Phase 3: Pipeline Execution

### Stage 1: Extraction

Reads SVO2 files and extracts frame data to disk.

**Process:**
1. Open SVO2 with ZED SDK
2. Iterate frames with configured skip interval
3. Extract RGB, depth, and point cloud data
4. Apply diversity filter (if enabled)
5. Create `frame_registry.json`
6. Ingest frame records to database

**Output Structure:**
```
{job_id}/{sequence}/
├── image_left/
│   └── 000000.png, 000001.png, ...
├── image_right/
│   └── 000000.png, 000001.png, ...
├── depth/
│   └── 000000.npy, 000001.npy, ...
├── velodyne/
│   └── 000000.bin, 000001.bin, ...
└── frame_registry.json
```

### Stage 2: Segmentation

Runs SAM3 object detection and segmentation.

**Process:**
1. Load SAM3 model (configurable variant)
2. Process frames in batches
3. Generate bounding boxes and masks
4. Compute confidence scores
5. Save detection results

**Output:**
```
{sequence}/detections/
├── detections.json
└── masks/
    └── 000000_0.png, 000000_1.png, ...
```

### Stage 3: Reconstruction

Projects 2D detections to 3D space.

**Process:**
1. Load depth maps and camera calibration
2. Project detection masks to 3D points
3. Estimate 3D bounding boxes using PCA
4. Transform to KITTI coordinate system
5. Save labels in KITTI format

**Output:**
```
{sequence}/label_2/
└── 000000.txt, 000001.txt, ...
```

### Stage 4: Tracking

Associates detections across frames.

**Process:**
1. Load 3D detections from all frames
2. Run ByteTrack association algorithm
3. Assign persistent track IDs
4. Save tracking results

**Output:**
```
{sequence}/tracks.json
```

### Job State Machine

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ start
                         ▼
    ┌──────────────────────────────────────┐
    │              RUNNING                 │
    │                                      │
    │  ┌────────┐ ┌────────┐ ┌────────┐   │
    │  │Extract │→│Segment │→│Reconstr│→...│
    │  └────────┘ └────────┘ └────────┘   │
    └───────┬─────────┬─────────┬─────────┘
            │         │         │
       ┌────┘    ┌────┘         └────┐
       ▼         ▼                   ▼
  ┌────────┐ ┌────────┐         ┌────────┐
  │COMPLETE│ │ PAUSED │         │ FAILED │
  └────────┘ └───┬────┘         └───┬────┘
                 │ resume           │ restart
                 └──────▶ RUNNING ◀─┘
```

---

## Phase 4: Review and Curation

The Review phase enables quality control and data filtering before export.

### Annotation Statistics

The system provides aggregated statistics for informed filtering:

| Metric | Description |
|--------|-------------|
| Total count | Detections per class |
| Frame count | Frames containing class |
| Average confidence | Mean confidence score |
| Min/Max confidence | Confidence range |

### Filtering Options

| Filter Type | Description | Scope |
|-------------|-------------|-------|
| Class Exclusion | Remove entire object classes | Global |
| Annotation Exclusion | Remove individual detections | Per-annotation |
| Frame Exclusion | Remove specific frames | Per-frame |
| Diversity Filtering | Remove similar/static frames | Algorithmic |

### Diversity Analysis

The diversity filter uses two metrics:

1. **Perceptual Hash (dHash)**
   - Computes difference hash for visual similarity
   - Configurable similarity threshold
   - Removes near-duplicate frames

2. **Motion Score**
   - Measures inter-frame pixel differences
   - Configurable motion threshold
   - Removes static/low-motion frames

### Curated Dataset (Optional)

Users may save filter configurations as immutable snapshots:

| Field | Description |
|-------|-------------|
| `version` | Auto-incremented per source job |
| `filter_config` | Immutable filter configuration |
| `excluded_frame_ids` | List of excluded frames |
| `excluded_annotation_ids` | List of excluded annotations |
| `exclusion_reasons` | Documented rationale |
| `original_count` | Pre-filter totals |
| `filtered_count` | Post-filter totals |

**Benefits:**
- Reproducibility across exports
- Version comparison
- Audit trail

---

## Phase 5: Training Dataset Export

### Export Configuration

| Parameter | Options | Description |
|-----------|---------|-------------|
| `format` | kitti, coco, both | Output format(s) |
| `train_ratio` | 0.0-1.0 | Training set proportion |
| `val_ratio` | 0.0-1.0 | Validation set proportion |
| `test_ratio` | 0.0-1.0 | Test set proportion |
| `include_masks` | bool | Include segmentation masks |
| `include_depth` | bool | Include depth maps |
| `include_3d_boxes` | bool | Include 3D bounding boxes |

### Export Process

1. **Load Data** - Read frames and annotations from job output
2. **Apply Filters** - Remove excluded classes, annotations, frames
3. **Split Data** - Divide into train/val/test sets
4. **Export Formats** - Write to selected format(s)
5. **Create Lineage** - Document full provenance
6. **Finalize** - Update statistics and paths

### KITTI Format Structure

```
kitti/
├── train/
│   ├── image_2/
│   │   └── 000000.png, 000001.png, ...
│   ├── label_2/
│   │   └── 000000.txt, 000001.txt, ...
│   ├── depth/
│   │   └── 000000.npy, 000001.npy, ...
│   └── masks/
│       └── 000000_0.png, ...
├── val/
│   └── [same structure]
└── test/
    └── [same structure]
```

### COCO Format Structure

```
coco/
├── train/
│   ├── images/
│   │   └── 000000.png, 000001.png, ...
│   ├── masks/
│   │   └── 000000_0.png, ...
│   └── annotations.json
├── val/
│   └── [same structure]
└── test/
    └── [same structure]
```

### Lineage Document

Each export includes `lineage.json`:

```json
{
  "training_dataset_id": "uuid",
  "source_job_id": "uuid",
  "source_dataset_id": "uuid",
  "curated_dataset_id": "uuid",
  "filter_config": { ... },
  "split_config": { ... },
  "format": "kitti",
  "statistics": {
    "total_frames": 1000,
    "total_annotations": 5000,
    "train_frames": 700,
    "val_frames": 200,
    "test_frames": 100
  },
  "created_at": "2026-01-14T12:00:00Z"
}
```

---

## Flow Variations

### Variation 1: Minimal Flow

**Path:** Direct Files → Full Pipeline → Direct Export

```
Browse SVO2 → Create Job → Start → Complete → Export Training Dataset
```

- No dataset record
- No curated snapshot
- Fastest path

### Variation 2: Full Lineage Flow

**Path:** Dataset Import → Full Pipeline → Curated Snapshot → Export

```
Create Dataset → Scan → Prepare → Create Job → Start → Complete
    → Review → Save Curated → Export Training Dataset
```

- Complete provenance chain
- Reproducible curation
- Production recommended

### Variation 3: Selective Stages

**Path:** Limited Pipeline Execution

```
Create Job (stages: [extraction, segmentation]) → Start → Complete
```

- Dependencies auto-resolved
- Progress normalized to selected stages
- Use case: Quick annotation without 3D

### Variation 4: Iterative Curation

**Path:** Multiple Curated Versions

```
Complete Job → Review → Save v1 → Adjust → Save v2 → Export from v2
```

- Compare filtering strategies
- Auto-versioned per job
- A/B testing workflows

### Variation 5: Pipeline Recovery

**Path:** Interrupted Execution

```
Start → Running → Pause → Paused → Resume → Running → Complete
```
or
```
Start → Running → Failed → Restart → Running → Complete
```

- Pause preserves position
- Restart resets with same config
- Fault tolerance

### Variation 6: Extraction-Time Diversity

**Path:** Pre-filtered Extraction

```
Create Job (diversity_filter: true) → Start → [Filtered Extraction] → ...
```

- Frame deduplication at source
- Reduced pipeline workload
- Configurable thresholds

### Variation 7: Post-Processing Diversity

**Path:** Review-Time Diversity Analysis

```
Complete → Review → Analyze Diversity → Adjust → Re-analyze → Export
```

- Cached for fast iteration
- Visual cluster inspection
- Interactive threshold tuning

---

## Data Model Reference

### Entity Relationships

```
Dataset (1) ─────────────────── (N) DatasetFile
                                       │
                                       │ source
                                       ▼
ProcessingJob (1) ─────────────── (N) Frame ────── (N) Detection
       │                               │
       │                               │ included in
       │                               ▼
       │                        TrainingDatasetFrame
       │                               │
       │ source                        │ belongs to
       ▼                               ▼
CuratedDataset ─────────────────► TrainingDataset
```

### Key Models

| Model | Purpose |
|-------|---------|
| `Dataset` | Collection of SVO2 files from a source folder |
| `DatasetFile` | Individual SVO2 file with metadata |
| `ProcessingJob` | Pipeline execution instance |
| `JobConfig` | Processing parameters |
| `Frame` | Extracted frame with paths and status |
| `CuratedDataset` | Immutable filter configuration snapshot |
| `TrainingDataset` | Exported dataset with splits |
| `TrainingDatasetFrame` | Frame-level export lineage |

---

## API Reference

### File Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/files/browse` | GET | Browse filesystem for SVO2 files |
| `/files/frame-count` | GET | Get frame count from SVO2 |
| `/files/metadata/{path}` | GET | Get SVO2 metadata |
| `/files/validate` | POST | Validate SVO2 integrity |

### Dataset Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/datasets` | POST | Create dataset |
| `/datasets/{id}/scan` | POST | Scan folder for SVO2 files |
| `/datasets/{id}/prepare` | POST | Prepare files for processing |

### Job Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs/create` | POST | Create processing job |
| `/jobs/{id}/start` | POST | Start pending job |
| `/jobs/{id}/pause` | POST | Pause running job |
| `/jobs/{id}/resume` | POST | Resume paused job |
| `/jobs/{id}/cancel` | POST | Cancel job |
| `/jobs/{id}/restart` | POST | Restart failed job |

### Review Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs/{id}/annotation-stats` | POST | Get class statistics |
| `/jobs/{id}/frames/batch` | GET | Get frame batch |
| `/jobs/{id}/diversity/analyze` | POST | Analyze frame diversity |
| `/jobs/{id}/training-dataset` | POST | Create training dataset |

### Curated Dataset Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/curated-datasets` | POST | Create curated dataset |
| `/curated-datasets` | GET | List curated datasets |
| `/curated-datasets/{id}` | GET | Get curated dataset |
| `/curated-datasets/{id}` | PATCH | Update name/description |
| `/curated-datasets/{id}` | DELETE | Delete curated dataset |

### Training Dataset Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/training-datasets` | GET | List training datasets |
| `/training-datasets/{id}` | GET | Get training dataset |
| `/training-datasets/{id}/status` | GET | Get export status |
| `/training-datasets/{id}/download/{format}` | GET | Download as ZIP |

---

## File Reference

### Backend

| Component | Path |
|-----------|------|
| File routes | `backend/app/api/routes/files.py` |
| Dataset routes | `backend/app/api/routes/datasets.py` |
| Job routes | `backend/app/api/routes/jobs.py` |
| Review routes | `backend/app/api/routes/review.py` |
| Curated dataset routes | `backend/app/api/routes/curated_datasets.py` |
| Job service | `backend/app/services/job_service.py` |
| Dataset service | `backend/app/services/dataset_service.py` |
| Review service | `backend/app/services/review_service.py` |
| Training dataset service | `backend/app/services/training_dataset_service.py` |
| Curated dataset service | `backend/app/services/curated_dataset_service.py` |
| Diversity service | `backend/app/services/diversity_service.py` |

### Worker

| Component | Path |
|-----------|------|
| Orchestrator | `worker/tasks/orchestrator.py` |
| Extraction task | `worker/tasks/extraction.py` |
| Segmentation task | `worker/tasks/segmentation.py` |
| Reconstruction task | `worker/tasks/reconstruction.py` |
| Tracking task | `worker/tasks/tracking.py` |
| Export task | `worker/tasks/training_export.py` |
| Database operations | `worker/db.py` |

### Processing

| Component | Path |
|-----------|------|
| SVO2 reader | `processing/svo2/reader.py` |
| SVO2 extractor | `processing/svo2/extractor.py` |
| Frame registry | `processing/svo2/frame_registry.py` |
| SAM3 predictor | `processing/sam3/predictor.py` |

### Frontend

| Component | Path |
|-----------|------|
| Review components | `frontend/src/components/review/` |
| Job components | `frontend/src/components/jobs/` |
| Services | `frontend/src/services/` |
| Types | `frontend/src/types/` |

---

*Document generated by system analysis on January 14, 2026*
