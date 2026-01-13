/**
 * Review mode and training dataset API service.
 */

import api from './api';
import type {
  AnnotationStatsResponse,
  DiversityAnalysisRequest,
  DiversityAnalysisResponse,
  FrameBatchResponse,
  TrainingDatasetDetail,
  TrainingDatasetListResponse,
  TrainingDatasetRequest,
  TrainingDatasetResponse,
} from '../types/review';

export const reviewService = {
  /**
   * Get aggregated annotation statistics by class for filtering UI.
   */
  getAnnotationStats: async (jobId: string): Promise<AnnotationStatsResponse> => {
    const { data } = await api.get<AnnotationStatsResponse>(
      `/review/jobs/${jobId}/annotation-stats`
    );
    return data;
  },

  /**
   * Get batch of frames for video playback buffering.
   */
  getFramesBatch: async (
    jobId: string,
    startIndex: number = 0,
    count: number = 24
  ): Promise<FrameBatchResponse> => {
    const { data } = await api.get<FrameBatchResponse>(
      `/review/jobs/${jobId}/frames/batch`,
      {
        params: { start_index: startIndex, count },
      }
    );
    return data;
  },

  /**
   * Analyze frame diversity using perceptual hashing and motion estimation.
   */
  analyzeDiversity: async (
    jobId: string,
    request: DiversityAnalysisRequest
  ): Promise<DiversityAnalysisResponse> => {
    const { data } = await api.post<DiversityAnalysisResponse>(
      `/review/jobs/${jobId}/diversity/analyze`,
      request
    );
    return data;
  },

  /**
   * Get diversity analysis status or compute with given thresholds.
   */
  getDiversityStatus: async (
    jobId: string,
    similarityThreshold: number = 0.85,
    motionThreshold: number = 0.02
  ): Promise<DiversityAnalysisResponse> => {
    const { data } = await api.get<DiversityAnalysisResponse>(
      `/review/jobs/${jobId}/diversity/status`,
      {
        params: {
          similarity_threshold: similarityThreshold,
          motion_threshold: motionThreshold,
        },
      }
    );
    return data;
  },

  /**
   * Create a new training dataset from filtered job results.
   */
  createTrainingDataset: async (
    jobId: string,
    request: TrainingDatasetRequest
  ): Promise<TrainingDatasetResponse> => {
    const { data } = await api.post<TrainingDatasetResponse>(
      `/review/jobs/${jobId}/training-dataset`,
      request
    );
    return data;
  },

  /**
   * List all training datasets.
   */
  listTrainingDatasets: async (
    jobId?: string
  ): Promise<TrainingDatasetListResponse> => {
    const { data } = await api.get<TrainingDatasetListResponse>(
      '/review/training-datasets',
      {
        params: jobId ? { job_id: jobId } : undefined,
      }
    );
    return data;
  },

  /**
   * Get training dataset details including lineage.
   */
  getTrainingDataset: async (
    datasetId: string
  ): Promise<TrainingDatasetDetail> => {
    const { data } = await api.get<TrainingDatasetDetail>(
      `/review/training-datasets/${datasetId}`
    );
    return data;
  },

  /**
   * Get training dataset export status.
   */
  getTrainingDatasetStatus: async (
    datasetId: string
  ): Promise<TrainingDatasetResponse> => {
    const { data } = await api.get<TrainingDatasetResponse>(
      `/review/training-datasets/${datasetId}/status`
    );
    return data;
  },

  /**
   * Get download URL for training dataset.
   */
  getDownloadUrl: (datasetId: string, format: 'kitti' | 'coco'): string => {
    return `/api/review/training-datasets/${datasetId}/download/${format}`;
  },
};

export default reviewService;
