/**
 * Pipeline One - Curated Dataset Service
 */

import api from './api';
import type {
  CuratedDataset,
  CuratedDatasetListResponse,
  CreateCuratedDatasetRequest,
  UpdateCuratedDatasetRequest,
} from '../types/curated_dataset';

const BASE_URL = '/curated-datasets';

export const curatedDatasetService = {
  /**
   * Create a new curated dataset
   */
  async create(request: CreateCuratedDatasetRequest): Promise<CuratedDataset> {
    const { data } = await api.post<CuratedDataset>(BASE_URL, request);
    return data;
  },

  /**
   * Get a curated dataset by ID
   */
  async get(id: string): Promise<CuratedDataset> {
    const { data } = await api.get<CuratedDataset>(`${BASE_URL}/${id}`);
    return data;
  },

  /**
   * List curated datasets
   */
  async list(params?: {
    limit?: number;
    offset?: number;
    job_id?: string;
  }): Promise<CuratedDatasetListResponse> {
    const { data } = await api.get<CuratedDatasetListResponse>(BASE_URL, { params });
    return data;
  },

  /**
   * Update a curated dataset
   */
  async update(id: string, request: UpdateCuratedDatasetRequest): Promise<CuratedDataset> {
    const { data } = await api.patch<CuratedDataset>(`${BASE_URL}/${id}`, request);
    return data;
  },

  /**
   * Delete a curated dataset
   */
  async delete(id: string): Promise<void> {
    await api.delete(`${BASE_URL}/${id}`);
  },
};
