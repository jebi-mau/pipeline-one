/**
 * Pipeline One - Job type definitions
 */

export type JobStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

export type PipelineStage = 'extraction' | 'segmentation' | 'reconstruction' | 'tracking';

export const ALL_PIPELINE_STAGES: PipelineStage[] = ['extraction', 'segmentation', 'reconstruction', 'tracking'];

export const STAGE_INFO: Record<PipelineStage, { name: string; description: string; number: number }> = {
  extraction: { name: 'Extraction', description: 'Extract frames from SVO2 files', number: 1 },
  segmentation: { name: 'Segmentation', description: 'Run SAM3 object detection', number: 2 },
  reconstruction: { name: '3D Reconstruction', description: 'Generate 3D bounding boxes', number: 3 },
  tracking: { name: 'Tracking', description: 'Track objects across frames', number: 4 },
};

export type StageStatus = 'pending' | 'running' | 'completed' | 'skipped';

export interface StageETA {
  stage: string;
  stage_number: number;
  status: StageStatus;
  eta_seconds: number | null;
  elapsed_seconds: number | null;
}

export interface JobConfig {
  object_class_ids?: string[];
  sam3_model_variant?: string;
  /** Confidence threshold for SAM3 detections (0-1) */
  sam3_confidence_threshold?: number;
  /** IOU threshold for non-max suppression */
  sam3_iou_threshold?: number;
  /** Batch size for SAM3 inference */
  sam3_batch_size?: number;
  /** Frame skip interval (1 = process all frames) */
  frame_skip?: number;
  /** Enable object tracking across frames */
  enable_tracking?: boolean;
  /** Export 3D bounding box data */
  export_3d_data?: boolean;
  /** Pipeline stages to run */
  stages_to_run?: PipelineStage[];
  /** Enable frame diversity filtering during extraction */
  enable_diversity_filter?: boolean;
  /** Similarity threshold for diversity filter (0-1, higher = more strict) */
  diversity_similarity_threshold?: number;
  /** Motion threshold for diversity filter (0-1, min motion to keep frame) */
  diversity_motion_threshold?: number;
}

export interface Job {
  id: string;
  name: string;
  status: JobStatus;
  current_stage?: number;
  current_stage_name?: string | null;
  progress?: number;
  stage_progress?: number;
  total_frames?: number | null;
  processed_frames?: number | null;
  total_detections?: number | null;
  input_paths?: string[];
  input_files?: string[];
  object_classes?: string[];
  output_directory?: string | null;
  // Storage tracking
  storage_size_bytes?: number | null;
  storage_size_formatted?: string | null;
  config?: JobConfig;
  stages_to_run?: PipelineStage[];
  dataset_id?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  // ETA fields
  eta_seconds?: number | null;
  stage_etas?: StageETA[];
  frames_per_second?: number | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface JobCreate {
  name: string;
  input_paths?: string[];
  input_files?: string[];
  object_classes?: string[];
  output_directory?: string;
  config?: Partial<JobConfig>;
}

export interface JobStatusUpdate {
  id: string;
  status: string;
  message: string | null;
}

export interface JobStatistics {
  total_frames: number;
  total_detections: number;
  detections_by_class: Record<string, number>;
  total_tracks: number;
  processing_time_seconds: number;
}

export interface JobResults {
  job_id: string;
  status: string;
  statistics: JobStatistics;
  output_directory: string;
  available_exports: string[];
}

// Alias for backward compatibility
export type JobResponse = Job;

// Pre-job duration estimation types

export interface StageEstimate {
  frames: number;
  estimated_seconds: number;
  fps: number;
}

export type EstimateConfidence = 'low' | 'medium' | 'high';

export interface EstimateDurationRequest {
  svo2_files: string[];
  frame_skip?: number;
  sam3_model_variant?: string;
  stages_to_run?: PipelineStage[];
  total_frames?: number;
}

export interface EstimateDurationResponse {
  estimated_total_frames: number;
  estimated_duration_seconds: number;
  estimated_duration_formatted: string;
  breakdown: Record<string, StageEstimate>;
  confidence: EstimateConfidence;
  based_on_jobs: number;
}

export interface FrameCountResponse {
  total_frames: number;
  files: Array<{
    path: string;
    frame_count: number | null;
    error: string | null;
  }>;
}

// Storage estimation types

export interface EstimateStorageRequest {
  total_frames: number;
  stages_to_run?: PipelineStage[];
  frame_skip?: number;
  extract_point_clouds?: boolean;
  extract_right_image?: boolean;
  extract_masks?: boolean;
  image_format?: string;
}

export interface EstimateStorageResponse {
  estimated_bytes: number;
  estimated_formatted: string;
  available_bytes: number;
  available_formatted: string;
  sufficient_space: boolean;
  warning: string | null;
  details: {
    frames_to_process: number;
    stages: string[];
    extract_point_clouds: boolean;
    extract_right_image: boolean;
    extract_masks: boolean;
  };
}
