/**
 * Shalom - Data hooks using React Query for frame browsing and correlation
 */

import { useQuery } from '@tanstack/react-query';
import { dataService } from '../services';

// Query keys for cache management
export const dataKeys = {
  all: ['data'] as const,
  summary: (jobId: string) => [...dataKeys.all, 'summary', jobId] as const,
  frames: (jobId: string) => [...dataKeys.all, 'frames', jobId] as const,
  frameList: (jobId: string, params: Record<string, unknown>) =>
    [...dataKeys.frames(jobId), 'list', params] as const,
  frameDetail: (jobId: string, frameId: string) =>
    [...dataKeys.frames(jobId), 'detail', frameId] as const,
  correlation: (jobId: string, params: Record<string, unknown>) =>
    [...dataKeys.all, 'correlation', jobId, params] as const,
};

/**
 * Hook to fetch data summary for a job
 */
export function useDataSummary(jobId: string | undefined) {
  return useQuery({
    queryKey: dataKeys.summary(jobId!),
    queryFn: () => dataService.getSummary(jobId!),
    enabled: !!jobId,
    staleTime: 30000, // Cache for 30 seconds
  });
}

/**
 * Hook to fetch frame list for a job with pagination
 */
export function useFrameList(
  jobId: string | undefined,
  params?: { limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: dataKeys.frameList(jobId!, params || {}),
    queryFn: () => dataService.listFrames(jobId!, params),
    enabled: !!jobId,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch detailed frame information
 */
export function useFrameDetail(jobId: string | undefined, frameId: string | undefined) {
  return useQuery({
    queryKey: dataKeys.frameDetail(jobId!, frameId!),
    queryFn: () => dataService.getFrameDetail(jobId!, frameId!),
    enabled: !!jobId && !!frameId,
    staleTime: 60000, // Cache for 1 minute
  });
}

/**
 * Hook to fetch correlation table for a job
 */
export function useCorrelationTable(
  jobId: string | undefined,
  params?: { limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: dataKeys.correlation(jobId!, params || {}),
    queryFn: () => dataService.getCorrelationTable(jobId!, params),
    enabled: !!jobId,
    staleTime: 30000,
  });
}
