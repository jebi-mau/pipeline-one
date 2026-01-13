/**
 * Lineage API service for data traceability
 */

import api from './api';
import type {
  FrameLineage,
  SVO2Lineage,
  AnnotationLineage,
  DatasetSummary,
  LineageEventsResponse,
  LineageEvent,
} from '../types/lineage';

/**
 * Get complete lineage for a frame.
 */
export async function getFrameLineage(frameId: string): Promise<FrameLineage> {
  const response = await api.get<FrameLineage>(`/lineage/frame/${frameId}`);
  return response.data;
}

/**
 * Get lineage for an SVO2 file (DatasetFile).
 */
export async function getSVO2Lineage(datasetFileId: string): Promise<SVO2Lineage> {
  const response = await api.get<SVO2Lineage>(`/lineage/svo2/${datasetFileId}`);
  return response.data;
}

/**
 * Get lineage for an external annotation.
 */
export async function getAnnotationLineage(annotationId: string): Promise<AnnotationLineage> {
  const response = await api.get<AnnotationLineage>(`/lineage/annotation/${annotationId}`);
  return response.data;
}

/**
 * Get aggregated summary statistics for a dataset.
 */
export async function getDatasetSummary(datasetId: string): Promise<DatasetSummary> {
  const response = await api.get<DatasetSummary>(`/lineage/dataset/${datasetId}/summary`);
  return response.data;
}

/**
 * Get lineage events for audit trail.
 */
export async function getLineageEvents(params?: {
  datasetId?: string;
  jobId?: string;
  eventType?: string;
  limit?: number;
}): Promise<LineageEventsResponse> {
  const response = await api.get<LineageEventsResponse>('/lineage/events', { params });
  return response.data;
}

/**
 * Create a lineage event for audit trail.
 */
export async function createLineageEvent(data: {
  event_type: string;
  dataset_id?: string;
  job_id?: string;
  dataset_file_id?: string;
  frame_id?: string;
  details?: Record<string, unknown>;
}): Promise<LineageEvent> {
  const response = await api.post<LineageEvent>('/lineage/events', data);
  return response.data;
}
