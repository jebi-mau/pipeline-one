# SVO2-SAM3 Analyzer

A GPU-accelerated pipeline for processing ZED camera SVO2 recordings with SAM 3 (Segment Anything Model 3) for object detection, 3D reconstruction, and tracking.

## Features

- **SVO2 Frame Extraction**: Extract RGB, depth, and point cloud data from ZED camera recordings
- **SAM 3 Segmentation**: Text-prompt based object detection using Meta's Segment Anything Model 3
- **3D Reconstruction**: Estimate 3D bounding boxes from depth data
- **Object Tracking**: Track detected objects across frames using ByteTrack
- **GPU Acceleration**: Optimized for NVIDIA GPUs including RTX 5090 (CUDA 12.8)
- **Web Dashboard**: Real-time job monitoring and management
- **REST API**: Full API for programmatic access

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   FastAPI       │────▶│   Celery        │
│   (React)       │     │   Backend       │     │   Workers       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   PostgreSQL    │     │   Redis         │
                        │   (Jobs/Config) │     │   (Task Queue)  │
                        └─────────────────┘     └─────────────────┘
```

## Pipeline Stages

1. **Extraction** - Extract frames from SVO2 files (requires ZED SDK)
2. **Segmentation** - Run SAM 3 inference with text prompts
3. **Reconstruction** - Generate 3D bounding boxes from depth + masks
4. **Tracking** - Associate detections across frames

## Requirements

- Python 3.12+
- NVIDIA GPU with CUDA 12.8+ support
- Docker and Docker Compose
- ZED SDK (for SVO2 extraction)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/jebi-mau/pipeline-one.git
cd pipeline-one
```

### 2. Create virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install PyTorch with CUDA 12.8 (for RTX 5090 support)

```bash
pip install torch torchvision torchaudio
```

### 5. Start infrastructure services

```bash
docker-compose up -d
```

### 6. Run database migrations

```bash
alembic upgrade head
```

## Running the Application

### Start all services

```bash
# Terminal 1: Backend API
source .venv/bin/activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Celery Worker
source .venv/bin/activate
celery -A worker.celery_app worker -Q default,gpu --loglevel=info

# Terminal 3: Frontend (optional)
cd frontend && npm run dev
```

### Using the API

Create a processing job:

```bash
curl -X POST http://localhost:8000/api/jobs/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Processing Job",
    "input_paths": ["/path/to/recording.svo2"],
    "output_directory": "/path/to/output",
    "config": {
      "object_class_ids": ["person", "car", "truck"],
      "sam3_confidence_threshold": 0.5,
      "frame_skip": 5
    }
  }'
```

Start the job:

```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/start
```

Check job status:

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

## Configuration

### Environment Variables

Create a `.env` file:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=svo2_analyzer
POSTGRES_PASSWORD=svo2_analyzer_dev
POSTGRES_DB=svo2_analyzer

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# SAM 3
SAM3_MODEL_PATH=facebook/sam3
```

### Job Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `object_class_ids` | Classes to detect (e.g., "person", "car") | Required |
| `sam3_confidence_threshold` | Detection confidence threshold | 0.5 |
| `sam3_iou_threshold` | NMS IoU threshold | 0.7 |
| `sam3_batch_size` | Batch size for inference | 8 |
| `frame_skip` | Process every Nth frame | 1 |
| `enable_tracking` | Enable object tracking | true |
| `export_3d_data` | Generate 3D bounding boxes | true |

## Project Structure

```
pipe1/
├── backend/                 # FastAPI backend
│   └── app/
│       ├── api/            # API routes
│       ├── models/         # SQLAlchemy models
│       ├── schemas/        # Pydantic schemas
│       └── services/       # Business logic
├── frontend/               # React frontend
├── processing/             # Core processing modules
│   ├── sam3/              # SAM 3 integration
│   ├── svo2/              # SVO2 extraction
│   ├── reconstruction/    # 3D reconstruction
│   └── tracking/          # Object tracking
├── worker/                 # Celery workers
│   └── tasks/             # Task definitions
├── docker-compose.yml      # Infrastructure services
└── requirements.txt        # Python dependencies
```

## GPU Support

This project supports NVIDIA GPUs with CUDA 12.8+, including:

- RTX 4090
- RTX 5090 (Blackwell architecture, sm_120)

Verify GPU support:

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0)}")
print(f"Compute capability: {torch.cuda.get_device_capability(0)}")
```

## License

MIT License

## Acknowledgments

- [Meta SAM 3](https://github.com/facebookresearch/sam3) - Segment Anything Model 3
- [Stereolabs ZED SDK](https://www.stereolabs.com/developers) - ZED camera support
- [ByteTrack](https://github.com/ifzhang/ByteTrack) - Multi-object tracking
