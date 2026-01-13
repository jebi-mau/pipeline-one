/**
 * Dataset API service
 */

import api from './api';
import type {
  Dataset,
  DatasetCreate,
  DatasetDetail,
  DatasetListResponse,
  DatasetScanRequest,
  DatasetScanResponse,
  DatasetPrepareResponse,
  DatasetCamerasResponse,
} from '../types/dataset';

export const datasetService = {
  list: async (params?: {
    customer?: string;
    site?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<DatasetListResponse> => {
    const { data } = await api.get('/datasets', { params });
    return data;
  },

  get: async (datasetId: string): Promise<DatasetDetail> => {
    const { data } = await api.get(`/datasets/${datasetId}`);
    return data;
  },

  create: async (datasetData: DatasetCreate): Promise<Dataset> => {
    const { data } = await api.post('/datasets', datasetData);
    return data;
  },

  update: async (
    datasetId: string,
    datasetData: Partial<DatasetCreate>
  ): Promise<Dataset> => {
    const { data } = await api.patch(`/datasets/${datasetId}`, datasetData);
    return data;
  },

  delete: async (datasetId: string): Promise<void> => {
    await api.delete(`/datasets/${datasetId}`);
  },

  scan: async (
    datasetId: string,
    request: DatasetScanRequest
  ): Promise<DatasetScanResponse> => {
    const { data } = await api.post(`/datasets/${datasetId}/scan`, request);
    return data;
  },

  prepare: async (
    datasetId: string,
    outputDirectory?: string
  ): Promise<DatasetPrepareResponse> => {
    const { data } = await api.post(`/datasets/${datasetId}/prepare`, {
      output_directory: outputDirectory,
    });
    return data;
  },

  getCameras: async (datasetId: string): Promise<DatasetCamerasResponse> => {
    const { data } = await api.get(`/datasets/${datasetId}/cameras`);
    return data;
  },

  getFiles: async (
    datasetId: string,
    params?: { status?: string; camera_id?: string; limit?: number; offset?: number }
  ): Promise<{ files: any[]; total: number }> => {
    const { data } = await api.get(`/datasets/${datasetId}/files`, { params });
    return data;
  },
};
