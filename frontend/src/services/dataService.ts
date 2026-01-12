/**
 * Shalom - Data API service for frame browsing and correlation
 */

import api from './api';
import type {
  DataSummary,
  FrameListResponse,
  FrameDetail,
  CorrelationTableResponse,
} from '../types';

export const dataService = {
  /**
   * Get data summary for a job
   */
  getSummary: async (jobId: string): Promise<DataSummary> => {
    const { data } = await api.get(`/data/jobs/${jobId}/summary`);
    return data;
  },

  /**
   * List frames for a job with pagination
   */
  listFrames: async (
    jobId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<FrameListResponse> => {
    const { data } = await api.get(`/data/jobs/${jobId}/frames`, { params });
    return data;
  },

  /**
   * Get detailed information for a specific frame
   */
  getFrameDetail: async (jobId: string, frameId: string): Promise<FrameDetail> => {
    const { data } = await api.get(`/data/jobs/${jobId}/frames/${frameId}`);
    return data;
  },

  /**
   * Get URL for frame image
   */
  getImageUrl: (jobId: string, frameId: string, type: 'left' | 'right' | 'depth'): string => {
    return `/api/data/jobs/${jobId}/frames/${frameId}/image/${type}`;
  },

  /**
   * Get URL for frame point cloud
   */
  getPointCloudUrl: (jobId: string, frameId: string): string => {
    return `/api/data/jobs/${jobId}/frames/${frameId}/pointcloud`;
  },

  /**
   * Get correlation table for a job
   */
  getCorrelationTable: async (
    jobId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<CorrelationTableResponse> => {
    const { data } = await api.get(`/data/jobs/${jobId}/correlation`, { params });
    return data;
  },
};
