/**
 * Pipeline One - Job hooks using React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsService } from '../services';
import type { JobCreate } from '../types';

// Query keys for cache management
export const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...jobKeys.lists(), filters] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
  results: (id: string) => [...jobKeys.detail(id), 'results'] as const,
};

export function useJobs(params?: { status?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: jobKeys.list(params || {}),
    queryFn: () => jobsService.list(params),
    staleTime: 10000, // Consider data fresh for 10 seconds
    refetchInterval: 15000, // Auto-refresh every 15 seconds (reduced from 5s)
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: jobKeys.detail(jobId!),
    queryFn: () => jobsService.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Auto-refresh while job is running
      return data?.status === 'running' || data?.status === 'pending' ? 2000 : false;
    },
  });
}

export function useJobResults(jobId: string | undefined) {
  return useQuery({
    queryKey: jobKeys.results(jobId!),
    queryFn: () => jobsService.getResults(jobId!),
    enabled: !!jobId,
    staleTime: 60000, // Results don't change often - cache for 1 minute
    retry: 2,
  });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobData: JobCreate) => jobsService.create(jobData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
    retry: 2,
    retryDelay: 1000,
  });
}

export function useStartJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.start(jobId),
    onMutate: async (jobId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: jobKeys.detail(jobId) });
      // Snapshot previous value
      const previousJob = queryClient.getQueryData(jobKeys.detail(jobId));
      // Optimistically update to running
      queryClient.setQueryData(jobKeys.detail(jobId), (old: any) =>
        old ? { ...old, status: 'running' } : old
      );
      return { previousJob };
    },
    onError: (_, jobId, context) => {
      // Rollback on error
      if (context?.previousJob) {
        queryClient.setQueryData(jobKeys.detail(jobId), context.previousJob);
      }
    },
    onSettled: (_, __, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

export function usePauseJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.pause(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: jobKeys.detail(jobId) });
      const previousJob = queryClient.getQueryData(jobKeys.detail(jobId));
      queryClient.setQueryData(jobKeys.detail(jobId), (old: any) =>
        old ? { ...old, status: 'paused' } : old
      );
      return { previousJob };
    },
    onError: (_, jobId, context) => {
      if (context?.previousJob) {
        queryClient.setQueryData(jobKeys.detail(jobId), context.previousJob);
      }
    },
    onSettled: (_, __, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

export function useResumeJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.resume(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: jobKeys.detail(jobId) });
      const previousJob = queryClient.getQueryData(jobKeys.detail(jobId));
      queryClient.setQueryData(jobKeys.detail(jobId), (old: any) =>
        old ? { ...old, status: 'running' } : old
      );
      return { previousJob };
    },
    onError: (_, jobId, context) => {
      if (context?.previousJob) {
        queryClient.setQueryData(jobKeys.detail(jobId), context.previousJob);
      }
    },
    onSettled: (_, __, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.cancel(jobId),
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: jobKeys.detail(jobId) });
      const previousJob = queryClient.getQueryData(jobKeys.detail(jobId));
      queryClient.setQueryData(jobKeys.detail(jobId), (old: any) =>
        old ? { ...old, status: 'cancelled' } : old
      );
      return { previousJob };
    },
    onError: (_, jobId, context) => {
      if (context?.previousJob) {
        queryClient.setQueryData(jobKeys.detail(jobId), context.previousJob);
      }
    },
    onSettled: (_, __, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

export function useRestartJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.restart(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => jobsService.delete(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}
