/**
 * Storage and disk management type definitions
 */

export interface DiskUsage {
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  usage_percent: number;
  warning: string | null;
}

export interface OrphanedDirectory {
  name: string;
  path: string;
  size_bytes: number;
  size_human: string;
}

export interface OrphanedDirectoriesResponse {
  orphaned_count: number;
  total_size_bytes: number;
  total_size_human: string;
  orphans: OrphanedDirectory[];
}

export interface CleanupResult {
  deleted_count: number;
  deleted_size_bytes: number;
  deleted_size_human: string;
  failed_count: number;
  errors: string[];
}

export type WarningLevel = 'normal' | 'warning' | 'critical';

export interface StorageSummary {
  // Disk usage
  disk_total_bytes: number;
  disk_used_bytes: number;
  disk_free_bytes: number;
  disk_total_formatted: string;
  disk_used_formatted: string;
  disk_free_formatted: string;
  disk_usage_percent: number;

  // Per-entity storage
  total_jobs_storage_bytes: number;
  total_jobs_storage_formatted: string;
  total_datasets_storage_bytes: number;
  total_datasets_storage_formatted: string;
  total_training_datasets_bytes: number;
  total_training_datasets_formatted: string;

  // Warnings
  warning: string | null;
  warning_level: WarningLevel;
}

export interface BackfillResponse {
  jobs_found: number;
  jobs_updated: number;
  datasets_found: number;
  datasets_updated: number;
  total_size_bytes: number;
  total_size_formatted: string;
  dry_run: boolean;
  errors: string[];
}
