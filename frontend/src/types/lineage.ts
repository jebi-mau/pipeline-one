/**
 * Lineage type definitions for data traceability
 */

export interface FrameLineage {
  frame: {
    id: string;
    svo2_file_path: string;
    svo2_frame_index: number;
    original_svo2_filename: string | null;
    original_unix_timestamp: number | null;
    timestamp_ns: number;
    sequence_index: number;
    image_left_path: string | null;
    image_right_path: string | null;
    depth_path: string | null;
    numpy_path: string | null;
    extraction_status: string;
    created_at: string | null;
  };
  dataset_file: {
    id: string;
    original_filename: string;
    camera_serial: string | null;
    camera_model: string | null;
    frame_count: number | null;
    recording_start_ns: number | null;
    video_codec: string | null;
    compression_mode: string | null;
    status: string;
  } | null;
  dataset: {
    id: string;
    name: string;
    customer: string | null;
    site: string | null;
    equipment: string | null;
  } | null;
  job: {
    id: string;
    name: string;
    status: string;
    current_stage: number;
    depth_mode: string | null;
    started_at: string | null;
  } | null;
  annotations: Array<{
    id: string;
    label: string;
    annotation_type: string;
    bbox: [number, number, number, number] | null;
    match_strategy: string | null;
    source_image_name: string;
  }>;
  sensor_data: {
    imu: {
      accel: { x: number | null; y: number | null; z: number | null };
      gyro: { x: number | null; y: number | null; z: number | null };
      orientation: { w: number | null; x: number | null; y: number | null; z: number | null };
    };
    magnetometer: { x: number | null; y: number | null; z: number | null } | null;
    barometer: { pressure_hpa: number | null; altitude_m: number | null } | null;
    temperature: { imu_c: number | null; barometer_c: number | null };
  } | null;
}

export interface SVO2Lineage {
  dataset_file: {
    id: string;
    original_filename: string;
    original_path: string;
    renamed_filename: string | null;
    camera_serial: string | null;
    camera_model: string | null;
    file_size: number;
    frame_count: number | null;
    fps: number | null;
    recording_start_ns: number | null;
    recording_duration_ms: number | null;
    resolution: { width: number; height: number } | null;
    video_codec: string | null;
    compression_mode: string | null;
    bitrate_kbps: number | null;
    status: string;
  };
  dataset: {
    id: string;
    name: string;
    description: string | null;
    customer: string | null;
    site: string | null;
    equipment: string | null;
    status: string;
  } | null;
  frames: Array<{
    id: string;
    sequence_index: number;
    svo2_frame_index: number;
    timestamp_ns: number;
    extraction_status: string;
  }>;
  annotation_stats: {
    total_annotations: number;
    matched: number;
    unmatched: number;
  };
}

export interface AnnotationLineage {
  annotation: {
    id: string;
    label: string;
    annotation_type: string;
    bbox: [number, number, number, number] | null;
    points: Array<[number, number]> | null;
    source_image_name: string;
    match_strategy: string | null;
    source_frame_index: number | null;
    is_matched: boolean;
    match_confidence: number | null;
    created_at: string | null;
  };
  import_record: {
    id: string;
    source_tool: string;
    source_format: string;
    source_filename: string;
    status: string;
    imported_at: string | null;
  } | null;
  frame: {
    id: string;
    svo2_frame_index: number;
    sequence_index: number;
    timestamp_ns: number;
    original_svo2_filename: string | null;
  } | null;
  svo2_file: {
    id: string;
    original_filename: string;
    camera_serial: string | null;
  } | null;
  dataset: {
    id: string;
    name: string;
    customer: string | null;
    site: string | null;
  } | null;
}

export interface DatasetSummary {
  dataset: {
    id: string;
    name: string;
    description: string | null;
    customer: string | null;
    site: string | null;
    equipment: string | null;
    status: string;
    created_at: string | null;
  };
  files: {
    total: number;
    by_status: Record<string, number>;
    total_size_bytes: number;
    cameras: string[];
  };
  frames: {
    total: number;
    extracted: number;
  };
  annotations: {
    total_imports: number;
    total_annotations: number;
    matched: number;
    unmatched: number;
  };
  jobs: {
    total: number;
    by_status: Record<string, number>;
  };
}

export interface LineageEvent {
  id: string;
  event_type: string;
  dataset_id: string | null;
  job_id: string | null;
  dataset_file_id: string | null;
  frame_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface LineageEventsResponse {
  events: LineageEvent[];
  total: number;
}

// Breadcrumb segment types
export interface LineageBreadcrumbSegment {
  type: 'dataset' | 'svo2' | 'frame' | 'annotation';
  id: string;
  label: string;
  path: string;
}
