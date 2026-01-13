# SVO2 Data Traceability & Management Plan

## Overview

Implement full end-to-end data traceability for SVO2 processing pipeline, enabling complete lineage tracking from raw SVO2 files through disaggregation, annotation, and training data generation.

---

## Current State vs Requirements

| Requirement | Current State | Gap |
|-------------|---------------|-----|
| Dataset metadata (customer, site, equipment) | ✅ Implemented | None |
| SVO2 file tracking with camera serial | ✅ Implemented | None |
| Frame → SVO2 traceability | ⚠️ Field exists but not populated | **Critical** |
| NumPy array generation | ⚠️ Field exists, no implementation | **High** |
| Magnetometer IMU data | ❌ Not captured | Medium |
| Annotation → Frame → SVO2 lineage | ⚠️ Fragile filename matching | **High** |
| Lineage UI | ❌ Not implemented | **High** |
| Audit trail | ❌ Not implemented | Medium |

---

## Implementation Plan

### Phase 1: Core Traceability Infrastructure

#### 1.1 Populate Frame-to-DatasetFile Link During Extraction

**Files to modify:**
- `worker/tasks/extraction.py`
- `processing/svo2/extractor.py`
- `backend/app/services/job_service.py`

**Changes:**
1. When creating a job from a dataset, pass `dataset_file_id` mapping to extraction task
2. During frame creation, set `Frame.dataset_file_id` from the mapping
3. Store original SVO2 filename and Unix timestamp in frame metadata

```python
# In extraction task, receive dataset_file_mapping
dataset_file_mapping = {
    "/path/to/1704067200.svo2": "uuid-of-dataset-file",
    ...
}

# When creating Frame records
frame.dataset_file_id = dataset_file_mapping.get(svo2_path)
```

#### 1.2 Ingest Frame Registry into Database

**Files to modify:**
- `worker/tasks/extraction.py`
- `backend/app/services/data_service.py`

**Changes:**
1. After extraction completes, parse `frame_registry.json`
2. Create/update Frame records with full metadata
3. Store `svo2_frame_index`, `timestamp_ns`, original SVO2 hash

#### 1.3 Enhanced Frame Naming Convention

**New naming pattern:**
```
{dataset_id[:8]}_{svo2_timestamp}_{camera_serial}_{frame_index:06d}.png
```

Example: `a1b2c3d4_1704067200_12345678_000050.png`

This preserves:
- Dataset context
- Original SVO2 Unix timestamp
- Camera identification
- Frame sequence

---

### Phase 2: NumPy Array Generation

#### 2.1 Add NumPy Export to Extraction Pipeline

**Files to modify:**
- `processing/svo2/extractor.py`
- `worker/tasks/extraction.py`

**Changes:**
1. Add `extract_numpy: bool` to ExtractionConfig
2. Save RGB frames as `.npy` files alongside PNG
3. Store path in `Frame.numpy_path`

**Output structure:**
```
output_dir/
├── image_2/           # Left RGB PNG (for CVAT annotation)
├── image_3/           # Right RGB PNG
├── numpy/             # NumPy arrays for training
│   ├── left/          # Left camera arrays
│   │   └── 000000.npy
│   └── right/         # Right camera arrays
├── depth/
├── depth_numpy/       # Depth as NumPy (float32 meters)
└── ...
```

#### 2.2 NumPy Array Metadata

Each `.npy` file will have companion metadata:
```json
{
  "source_svo2": "1704067200.svo2",
  "dataset_id": "uuid",
  "dataset_file_id": "uuid",
  "frame_index": 50,
  "timestamp_ns": 1704067200123456789,
  "camera_serial": "12345678",
  "resolution": [1920, 1080],
  "dtype": "uint8",
  "channels": 3
}
```

---

### Phase 3: Complete Sensor Data Capture

#### 3.1 Full Sensor Suite from ZED SDK

**Files to modify:**
- `processing/svo2/reader.py`
- `backend/app/models/frame.py` (FrameMetadata)
- `backend/app/models/dataset.py` (DatasetFile)

**Sensor data to capture (via `get_sensors_data()`):**
```python
@dataclass
class SensorData:
    # IMU - Accelerometer (m/s²)
    accel_x: float
    accel_y: float
    accel_z: float

    # IMU - Gyroscope (rad/s)
    gyro_x: float
    gyro_y: float
    gyro_z: float

    # IMU - Magnetometer (µT)
    mag_x: float | None
    mag_y: float | None
    mag_z: float | None

    # Barometer
    pressure_hpa: float | None  # Atmospheric pressure (hPa)
    altitude_m: float | None    # Estimated altitude (m)

    # Temperature
    imu_temperature_c: float | None      # IMU sensor temp
    barometer_temperature_c: float | None # Barometer temp

    # Orientation (quaternion)
    orientation_w: float
    orientation_x: float
    orientation_y: float
    orientation_z: float

    # Timestamps
    timestamp_ns: int           # Nanosecond precision
    timestamp_relative_ms: float
```

#### 3.2 Video Container Metadata

**Add to DatasetFile model:**
```python
# Video encoding info (from SVO2 header)
video_codec: str | None        # "H264", "H265/HEVC", etc.
pixel_format: str | None       # "BGRA", "NV12", etc.
compression_mode: str | None   # "LOSSLESS", "LOSSY"
bitrate_kbps: int | None       # Video bitrate
```

**Note on depth maps:**
- Depth is NOT stored in SVO2 files
- Depth is COMPUTED using ZED SDK during extraction
- Store depth computation settings:
  ```python
  depth_mode: str  # "NEURAL", "ULTRA", "QUALITY", "PERFORMANCE"
  depth_range_min_m: float
  depth_range_max_m: float
  ```

#### 3.3 Enhanced Sensor Output Format

**New sensor output structure:**
```
output_dir/
├── sensors/
│   ├── imu/
│   │   └── 000000.json        # Full IMU data per frame
│   ├── barometer/
│   │   └── barometer.csv      # Time-series barometer data
│   └── temperature/
│       └── temperature.csv    # Time-series temperature
├── oxts/                      # KITTI format (backward compat)
└── sensor_metadata.json       # Sensor calibration & specs
```

#### 3.4 IMU Correlation Enhancement

**Files to modify:**
- `backend/app/services/data_service.py`
- `backend/app/schemas/data.py`

**Changes:**
1. Add API endpoint to get sensor data for frame range
2. Support querying by timestamp range
3. Add sensor interpolation for frames without direct samples
4. Include all sensor types in frame detail response

---

### Phase 4: Annotation Traceability

#### 4.1 Enhanced Annotation Matching

**Files to modify:**
- `backend/app/services/annotation_service.py`
- `backend/app/models/external_annotation.py`

**Changes:**
1. Add `source_dataset_id` to ExternalAnnotation
2. Match by multiple strategies:
   - Filename (current)
   - Frame index from filename
   - Timestamp matching
3. Store match metadata:
   ```python
   match_strategy: str  # "filename", "frame_index", "timestamp"
   source_frame_index: int  # Parsed from annotation filename
   ```

#### 4.2 Annotation Import Enhancement

**Files to modify:**
- `backend/app/api/routes/annotations.py`
- `backend/app/schemas/annotation.py`

**Changes:**
1. When importing, require dataset_id context
2. Parse Unix timestamp from annotation filenames
3. Match to frames via timestamp proximity if filename fails
4. Report unmatched annotations with source SVO2 context

---

### Phase 5: Lineage Query APIs

#### 5.1 New API Endpoints

**File to create:** `backend/app/api/routes/lineage.py`

```python
# Trace frame lineage
GET /lineage/frame/{frame_id}
Response: {
  "frame": {...},
  "dataset_file": {...},  # Source SVO2
  "dataset": {...},       # Parent dataset
  "job": {...},           # Processing job
  "annotations": [...],   # External annotations
  "exports": [...]        # Training exports containing this frame
}

# Trace SVO2 file lineage
GET /lineage/svo2/{dataset_file_id}
Response: {
  "dataset_file": {...},
  "dataset": {...},
  "frames": [...],        # All extracted frames
  "annotation_stats": {
    "total_annotations": 150,
    "matched": 145,
    "unmatched": 5
  }
}

# Reverse lookup: annotation to source
GET /lineage/annotation/{annotation_id}
Response: {
  "annotation": {...},
  "frame": {...},
  "svo2_file": {...},
  "dataset": {...}
}
```

#### 5.2 Lineage Service

**File to create:** `backend/app/services/lineage_service.py`

Provides methods for:
- `get_frame_lineage(frame_id)`
- `get_svo2_lineage(dataset_file_id)`
- `get_annotation_lineage(annotation_id)`
- `get_dataset_summary(dataset_id)` - aggregated stats

---

### Phase 6: Frontend Lineage UI

#### 6.1 Lineage Breadcrumb Component

**File to create:** `frontend/src/components/common/LineageBreadcrumb.tsx`

Display: `Dataset > SVO2 File > Frame > Annotation`

Each segment clickable to navigate to detail view.

#### 6.2 Enhanced DatasetDetailPage

**File to modify:** `frontend/src/pages/DatasetDetailPage.tsx`

Add:
- SVO2 file list with extraction status
- Per-SVO2 frame counts and annotation match rates
- Click SVO2 → see all frames from that file
- Visual timeline of Unix timestamps

#### 6.3 Frame Lineage View

**File to create:** `frontend/src/pages/FrameDetailPage.tsx`

Shows:
- Frame image (left/right/depth)
- Source SVO2 file info
- Original Unix timestamp
- Camera serial number
- IMU data at this frame
- Annotations on this frame
- Link to download NumPy array

#### 6.4 Annotation Matching Dashboard

**File to create:** `frontend/src/components/annotations/AnnotationMatchingView.tsx`

Shows:
- Import summary per SVO2 file
- Matched vs unmatched counts
- Unmatched annotation list with source filenames
- Manual re-match capability

---

### Phase 7: Project/Job Creation Workflow Enhancement

#### 7.1 Unified Project Creation Flow

**Files to modify:**
- `frontend/src/components/jobs/CreateJobModal.tsx`
- `frontend/src/pages/DatasetsPage.tsx`

**New workflow:**
1. **Create Project** (Dataset):
   - Name, description
   - Customer, site, equipment
   - Source folder path
   - Auto-scan for SVO2 files

2. **Review SVO2 Files**:
   - Show discovered files with metadata
   - Display Unix timestamps, camera serials
   - Allow selection of subset

3. **Configure Extraction**:
   - Frame skip
   - Output formats (PNG, NumPy, depth format)
   - IMU extraction toggle

4. **Start Processing**:
   - Creates job linked to dataset
   - Tracks progress per SVO2 file
   - Shows real-time lineage building

#### 7.2 Bulk Operations

**File to modify:** `backend/app/api/routes/datasets.py`

Add endpoints:
- `POST /datasets/{id}/extract-all` - Extract all SVO2s
- `POST /datasets/{id}/export-training` - Export matched annotations
- `GET /datasets/{id}/summary` - Full dataset stats

---

## Database Schema Changes

### New/Modified Tables

```sql
-- Add to frames table (lineage tracking)
ALTER TABLE frames ADD COLUMN original_svo2_filename VARCHAR(255);
ALTER TABLE frames ADD COLUMN original_unix_timestamp BIGINT;

-- Add to dataset_files table (video container metadata)
ALTER TABLE dataset_files ADD COLUMN video_codec VARCHAR(50);
ALTER TABLE dataset_files ADD COLUMN pixel_format VARCHAR(50);
ALTER TABLE dataset_files ADD COLUMN compression_mode VARCHAR(50);
ALTER TABLE dataset_files ADD COLUMN bitrate_kbps INTEGER;

-- Add to frame_metadata table (full sensor suite)
ALTER TABLE frame_metadata ADD COLUMN mag_x FLOAT;
ALTER TABLE frame_metadata ADD COLUMN mag_y FLOAT;
ALTER TABLE frame_metadata ADD COLUMN mag_z FLOAT;
ALTER TABLE frame_metadata ADD COLUMN pressure_hpa FLOAT;
ALTER TABLE frame_metadata ADD COLUMN altitude_m FLOAT;
ALTER TABLE frame_metadata ADD COLUMN imu_temperature_c FLOAT;
ALTER TABLE frame_metadata ADD COLUMN barometer_temperature_c FLOAT;

-- Add to external_annotations table (traceability)
ALTER TABLE external_annotations ADD COLUMN source_dataset_id UUID REFERENCES datasets(id);
ALTER TABLE external_annotations ADD COLUMN match_strategy VARCHAR(50);
ALTER TABLE external_annotations ADD COLUMN source_frame_index INTEGER;

-- Add to processing_jobs table (depth computation settings)
ALTER TABLE processing_jobs ADD COLUMN depth_mode VARCHAR(50);
ALTER TABLE processing_jobs ADD COLUMN depth_range_min_m FLOAT;
ALTER TABLE processing_jobs ADD COLUMN depth_range_max_m FLOAT;

-- New audit table
CREATE TABLE data_lineage_events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,  -- 'extraction', 'annotation_import', 'export'
    dataset_id UUID REFERENCES datasets(id),
    job_id UUID REFERENCES processing_jobs(id),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## File Summary

### Files to Create
| File | Purpose |
|------|---------|
| `backend/app/api/routes/lineage.py` | Lineage query endpoints |
| `backend/app/services/lineage_service.py` | Lineage traversal logic |
| `frontend/src/components/common/LineageBreadcrumb.tsx` | Breadcrumb navigation |
| `frontend/src/pages/FrameDetailPage.tsx` | Individual frame view |
| `frontend/src/components/annotations/AnnotationMatchingView.tsx` | Annotation dashboard |
| `alembic/versions/XXXXXX_add_lineage_fields.py` | Database migration |

### Files to Modify
| File | Changes |
|------|---------|
| `worker/tasks/extraction.py` | Populate dataset_file_id, save NumPy |
| `processing/svo2/extractor.py` | NumPy generation, enhanced naming |
| `processing/svo2/reader.py` | Magnetometer capture |
| `backend/app/models/frame.py` | Add lineage fields to FrameMetadata |
| `backend/app/services/annotation_service.py` | Enhanced matching |
| `backend/app/api/router.py` | Register lineage routes |
| `frontend/src/App.tsx` | Add FrameDetailPage route |
| `frontend/src/pages/DatasetDetailPage.tsx` | Enhanced SVO2 view |
| `frontend/src/components/jobs/CreateJobModal.tsx` | Unified workflow |

---

## Verification Plan

### 1. Data Traceability Test
```bash
# Create dataset
POST /datasets with source_folder="/data/raw/project1"

# Scan and verify SVO2 metadata
POST /datasets/{id}/scan
GET /datasets/{id} → verify camera serials, timestamps

# Create job and extract
POST /jobs with dataset_id
# Wait for completion

# Verify lineage
GET /lineage/frame/{any_frame_id}
# Should return: frame → dataset_file → dataset with all metadata
```

### 2. NumPy Array Test
```bash
# After extraction, verify:
ls output/{job_id}/*/numpy/left/*.npy
# Files should exist

# Verify metadata
python -c "import numpy as np; print(np.load('000000.npy').shape)"
# Should output (1080, 1920, 3) or similar
```

### 3. Annotation Lineage Test
```bash
# Import CVAT annotations
POST /datasets/{id}/annotations/import

# Check match stats
GET /annotations/imports/{import_id}/stats

# Trace annotation to source
GET /lineage/annotation/{annotation_id}
# Should return full chain to original SVO2
```

### 4. UI Verification
1. Create new dataset → verify metadata form
2. Scan folder → verify SVO2 list with timestamps
3. Click SVO2 → verify frame list
4. Click frame → verify lineage breadcrumb
5. Import annotations → verify match dashboard

---

## Implementation Order

All 7 phases will be implemented in logical dependency order:

| Order | Phase | Description | Dependencies |
|-------|-------|-------------|--------------|
| 1 | **Phase 1** | Core traceability (Frame → DatasetFile link) | None - Foundation |
| 2 | **Phase 3** | Complete sensor data capture (IMU, baro, temp, video metadata) | Phase 1 |
| 3 | **Phase 2** | NumPy array generation | Phase 1 |
| 4 | **Phase 4** | Annotation traceability | Phase 1 |
| 5 | **Phase 5** | Lineage query APIs | Phases 1, 3, 4 |
| 6 | **Phase 6** | Frontend lineage UI | Phase 5 |
| 7 | **Phase 7** | Workflow enhancement | Phase 6 |

**Estimated scope:** ~20-25 files modified/created

---

## Key Technical Notes

### SVO2 File Structure
- SVO2 files contain **stereo RGB video streams** (H.264/H.265 encoded)
- **Depth maps are NOT stored** in SVO2 - they are **computed** using ZED SDK's neural depth estimation
- Sensor data (IMU, barometer, temperature) is embedded in SVO2 and extracted via `get_sensors_data()`

### Data Flow Summary
```
SVO2 File (stored)
├── Left camera video (H.264/H.265)
├── Right camera video (H.264/H.265)
├── IMU data (accel, gyro, mag)
├── Barometer data
├── Temperature data
└── Camera calibration

     ↓ ZED SDK Extraction ↓

Disaggregated Output (computed/extracted)
├── image_2/ (Left RGB - decoded from video)
├── image_3/ (Right RGB - decoded from video)
├── numpy/ (NumPy arrays - from decoded frames)
├── depth/ (COMPUTED via neural depth estimation)
├── depth_numpy/ (Depth as NumPy arrays)
├── sensors/ (Extracted sensor time-series)
├── velodyne/ (Point clouds - computed from depth)
└── calib/ (Camera calibration)
```
