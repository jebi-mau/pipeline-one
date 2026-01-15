/**
 * Pipeline One - Curated Dataset types
 */

export interface FilterConfig {
  excluded_classes: string[];
  excluded_annotation_ids: string[];
  diversity_applied: boolean;
  diversity_similarity_threshold?: number;
  diversity_motion_threshold?: number;
  excluded_frame_indices: number[];
}

export interface ExclusionReasons {
  class_filter: string[];
  diversity: string[];
  manual: string[];
}

export interface CuratedDataset {
  id: string;
  name: string;
  description: string | null;
  version: number;
  source_job_id: string;
  source_job_name: string | null;
  source_dataset_id: string | null;
  source_dataset_name: string | null;
  source_raw_data_path: string | null;
  filter_config: FilterConfig;
  original_frame_count: number;
  original_annotation_count: number;
  filtered_frame_count: number;
  filtered_annotation_count: number;
  frames_removed: number;
  annotations_removed: number;
  reduction_percentage: number;
  excluded_frame_ids: string[];
  excluded_annotation_ids: string[];
  exclusion_reasons: ExclusionReasons;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  training_datasets_count: number;
}

export interface CuratedDatasetListItem {
  id: string;
  name: string;
  description: string | null;
  version: number;
  source_job_id: string;
  source_job_name: string | null;
  filtered_frame_count: number;
  filtered_annotation_count: number;
  training_datasets_count: number;
  created_at: string;
}

export interface CuratedDatasetListResponse {
  curated_datasets: CuratedDataset[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateCuratedDatasetRequest {
  name: string;
  description?: string;
  source_job_id: string;
  filter_config: FilterConfig;
  original_frame_count: number;
  original_annotation_count: number;
  filtered_frame_count: number;
  filtered_annotation_count: number;
  excluded_frame_ids: string[];
  excluded_annotation_ids: string[];
  exclusion_reasons: ExclusionReasons;
}

export interface UpdateCuratedDatasetRequest {
  name?: string;
  description?: string;
}
