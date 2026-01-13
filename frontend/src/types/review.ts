/**
 * Review mode and training dataset types.
 */

// =============================================================================
// Annotation Statistics
// =============================================================================

export interface AnnotationClassStats {
  class_name: string;
  class_color: string;
  total_count: number;
  frame_count: number;
  avg_confidence: number;
  annotation_ids: string[];
}

export interface AnnotationStatsResponse {
  job_id: string;
  total_annotations: number;
  total_frames: number;
  classes: AnnotationClassStats[];
}

// =============================================================================
// Frame Diversity Analysis
// =============================================================================

export interface DiversityAnalysisRequest {
  similarity_threshold: number;
  motion_threshold: number;
  sample_camera: 'left' | 'right';
}

export interface FrameCluster {
  representative_index: number;
  member_indices: number[];
  avg_similarity: number;
}

export interface DiversityAnalysisResponse {
  job_id: string;
  status: 'pending' | 'analyzing' | 'complete' | 'failed';
  error_message?: string;
  selected_frame_indices: number[];
  excluded_frame_indices: number[];
  clusters: FrameCluster[];
  original_frame_count: number;
  selected_frame_count: number;
  reduction_percent: number;
  duplicate_pairs_found: number;
  low_motion_frames: number;
  perceptual_hashes: Record<number, string>;
  motion_scores: Record<number, number>;
}

// =============================================================================
// Filter Configuration
// =============================================================================

export interface FilterConfiguration {
  excluded_classes: string[];
  excluded_annotation_ids: string[];
  excluded_frame_indices: number[];
  diversity_applied: boolean;
  similarity_threshold: number | null;
  motion_threshold: number | null;
}

// =============================================================================
// Training Dataset
// =============================================================================

export interface TrainingDatasetRequest {
  name: string;
  description?: string;
  format: 'kitti' | 'coco' | 'both';
  filter_config: FilterConfiguration;
  train_ratio: number;
  val_ratio: number;
  test_ratio: number;
  shuffle_seed?: number;
  include_masks: boolean;
  include_depth: boolean;
  include_3d_boxes: boolean;
}

export interface TrainingDatasetResponse {
  id: string;
  job_id: string;
  name: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  progress: number;
  total_frames: number;
  total_annotations: number;
  train_count: number;
  val_count: number;
  test_count: number;
  created_at: string;
}

export interface TrainingDatasetDetail extends TrainingDatasetResponse {
  description: string | null;
  format: string;
  filter_config: FilterConfiguration;
  source_job_id: string;
  source_job_name: string | null;
  source_dataset_id: string | null;
  source_dataset_name: string | null;
  output_directory: string | null;
  kitti_path: string | null;
  coco_path: string | null;
  file_size_bytes: number | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface TrainingDatasetListResponse {
  datasets: TrainingDatasetResponse[];
  total: number;
}

// =============================================================================
// Frame Batch for Playback
// =============================================================================

export interface FrameThumbnail {
  frame_id: string;
  sequence_index: number;
  svo2_frame_index: number;
  thumbnail_url: string;
  annotation_count: number;
}

export interface FrameBatchResponse {
  job_id: string;
  frames: FrameThumbnail[];
  total_frames: number;
  start_index: number;
  has_more: boolean;
}

// =============================================================================
// Playback State
// =============================================================================

export type PlaybackSpeed = 0.25 | 0.5 | 1 | 2 | 4;

export interface PlaybackState {
  isPlaying: boolean;
  speed: PlaybackSpeed;
  currentFrameIndex: number;
}
