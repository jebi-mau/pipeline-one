/**
 * Shalom - Job type definitions for SVO2-SAM3 Analyzer
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

export interface JobConfig {
  object_class_ids?: string[];
  sam3_model_variant?: string;
  sam3_confidence_threshold?: number;
  sam3_confidence?: number;
  sam3_iou_threshold?: number;
  sam3_batch_size?: number;
  batch_size?: number;
  frame_skip?: number;
  enable_tracking?: boolean;
  export_3d_data?: boolean;
  stages_to_run?: PipelineStage[];
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
  input_paths?: string[];
  input_files?: string[];
  object_classes?: string[];
  output_directory?: string | null;
  config?: JobConfig;
  stages_to_run?: PipelineStage[];
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  eta_seconds?: number | null;
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
