/**
 * Dataset type definitions
 */

export interface DatasetFileSummary {
  id: string;
  original_filename: string;
  relative_path: string;
  camera_id: string | null;
  camera_model: string | null;
  file_size: number;
  frame_count: number | null;
  resolution: string | null;
  fps: number | null;
  status: string;
  error_message: string | null;
}

export interface JobSummary {
  id: string;
  name: string;
  status: string;
  progress: number | null;
  current_stage_name: string | null;
  total_frames: number | null;
  processed_frames: number | null;
  object_classes: string[];
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface JobStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  jobs: JobSummary[];
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  customer: string | null;
  site: string | null;
  equipment: string | null;
  collection_date: string | null;
  object_types: string[];
  source_folder: string;
  output_directory: string | null;
  status: string;
  total_files: number;
  total_size_bytes: number;
  prepared_files: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  job_stats: JobStats;
}

export interface DatasetDetail extends Dataset {
  files: DatasetFileSummary[];
  job_count: number;
}

export interface DatasetCreate {
  name: string;
  description?: string;
  customer?: string;
  site?: string;
  equipment?: string;
  collection_date?: string;
  object_types?: string[];
  source_folder: string;
  output_directory?: string;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
  limit: number;
  offset: number;
}

export interface DatasetScanRequest {
  recursive: boolean;
  extract_metadata: boolean;
}

export interface DatasetScanResponse {
  dataset_id: string;
  files_found: number;
  files_added: number;
  duplicates_skipped: number;
  total_size_bytes: number;
  errors: string[];
}

export interface DatasetPrepareResponse {
  dataset_id: string;
  status: string;
  files_to_prepare: number;
  message: string;
}

export interface CameraInfo {
  camera_id: string;
  camera_model: string | null;
  camera_serial: string | null;
  file_count: number;
  total_frames: number | null;
}

export interface DatasetCamerasResponse {
  dataset_id: string;
  cameras: CameraInfo[];
}

export const datasetStatusColors: Record<string, string> = {
  created: 'bg-gray-500',
  scanning: 'bg-yellow-500',
  scanned: 'bg-blue-500',
  preparing: 'bg-orange-500',
  ready: 'bg-green-500',
  processing: 'bg-purple-500',
  completed: 'bg-green-600',
  failed: 'bg-red-500',
};

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
