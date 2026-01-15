/**
 * Storage management service
 */

import api from './api';
import type {
  DiskUsage,
  OrphanedDirectoriesResponse,
  CleanupResult,
  StorageSummary,
  BackfillResponse,
} from '../types/storage';
import type { EstimateStorageRequest, EstimateStorageResponse } from '../types/job';

const BASE_PATH = '/cleanup';

export const storageService = {
  /**
   * Get current disk usage for the output directory
   */
  async getDiskUsage(): Promise<DiskUsage> {
    const response = await api.get<DiskUsage>(`${BASE_PATH}/disk-usage`);
    return response.data;
  },

  /**
   * Get comprehensive storage breakdown by entity type
   */
  async getStorageSummary(): Promise<StorageSummary> {
    const response = await api.get<StorageSummary>(`${BASE_PATH}/storage-summary`);
    return response.data;
  },

  /**
   * List orphaned directories (exist on disk but not in database)
   */
  async listOrphanedDirectories(): Promise<OrphanedDirectoriesResponse> {
    const response = await api.get<OrphanedDirectoriesResponse>(`${BASE_PATH}/orphans`);
    return response.data;
  },

  /**
   * Delete all orphaned directories
   */
  async deleteOrphanedDirectories(): Promise<CleanupResult> {
    const response = await api.delete<CleanupResult>(`${BASE_PATH}/orphans`);
    return response.data;
  },

  /**
   * Backfill storage sizes for existing jobs and datasets
   */
  async backfillStorageSizes(dryRun: boolean = true): Promise<BackfillResponse> {
    const response = await api.post<BackfillResponse>(
      `${BASE_PATH}/backfill-storage`,
      null,
      { params: { dry_run: dryRun } }
    );
    return response.data;
  },

  /**
   * Estimate storage required for a job before creation
   */
  async estimateJobStorage(request: EstimateStorageRequest): Promise<EstimateStorageResponse> {
    const response = await api.post<EstimateStorageResponse>('/jobs/estimate-storage', request);
    return response.data;
  },
};
