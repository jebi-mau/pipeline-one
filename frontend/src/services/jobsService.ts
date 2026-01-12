/**
 * Shalom - Jobs API service
 */

import api from './api';
import type { Job, JobCreate, JobListResponse, JobStatusUpdate, JobResults } from '../types';

export const jobsService = {
  list: async (params?: { status?: string; limit?: number; offset?: number }): Promise<JobListResponse> => {
    const { data } = await api.get('/jobs', { params });
    return data;
  },

  get: async (jobId: string): Promise<Job> => {
    const { data } = await api.get(`/jobs/${jobId}`);
    return data;
  },

  create: async (jobData: JobCreate): Promise<Job> => {
    const { data } = await api.post('/jobs/create', jobData);
    return data;
  },

  start: async (jobId: string): Promise<JobStatusUpdate> => {
    const { data } = await api.post(`/jobs/${jobId}/start`);
    return data;
  },

  pause: async (jobId: string): Promise<JobStatusUpdate> => {
    const { data } = await api.post(`/jobs/${jobId}/pause`);
    return data;
  },

  resume: async (jobId: string): Promise<JobStatusUpdate> => {
    const { data } = await api.post(`/jobs/${jobId}/resume`);
    return data;
  },

  cancel: async (jobId: string): Promise<JobStatusUpdate> => {
    const { data } = await api.post(`/jobs/${jobId}/cancel`);
    return data;
  },

  restart: async (jobId: string): Promise<JobStatusUpdate> => {
    const { data } = await api.post(`/jobs/${jobId}/restart`);
    return data;
  },

  delete: async (jobId: string): Promise<void> => {
    await api.delete(`/jobs/${jobId}`);
  },

  getResults: async (jobId: string): Promise<JobResults> => {
    const { data } = await api.get(`/jobs/${jobId}/results`);
    return data;
  },
};
