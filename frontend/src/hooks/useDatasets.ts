/**
 * Dataset hooks using React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { datasetService } from '../services/datasetService';
import type { DatasetCreate, DatasetScanRequest } from '../types/dataset';

// Query keys for cache management
export const datasetKeys = {
  all: ['datasets'] as const,
  lists: () => [...datasetKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...datasetKeys.lists(), filters] as const,
  details: () => [...datasetKeys.all, 'detail'] as const,
  detail: (id: string) => [...datasetKeys.details(), id] as const,
  cameras: (id: string) => [...datasetKeys.detail(id), 'cameras'] as const,
  files: (id: string, filters: Record<string, unknown>) =>
    [...datasetKeys.detail(id), 'files', filters] as const,
};

export function useDatasets(params?: {
  customer?: string;
  site?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: datasetKeys.list(params || {}),
    queryFn: () => datasetService.list(params),
    staleTime: 10000,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });
}

export function useDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: datasetKeys.detail(datasetId!),
    queryFn: () => datasetService.get(datasetId!),
    enabled: !!datasetId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Auto-refresh while dataset is being processed
      return data?.status === 'scanning' || data?.status === 'preparing' ? 5000 : false;
    },
  });
}

export function useDatasetCameras(datasetId: string | undefined) {
  return useQuery({
    queryKey: datasetKeys.cameras(datasetId!),
    queryFn: () => datasetService.getCameras(datasetId!),
    enabled: !!datasetId,
    staleTime: 60000, // Cameras don't change often
  });
}

export function useDatasetFiles(
  datasetId: string | undefined,
  params?: { status?: string; camera_id?: string; limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: datasetKeys.files(datasetId!, params || {}),
    queryFn: () => datasetService.getFiles(datasetId!, params),
    enabled: !!datasetId,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datasetData: DatasetCreate) => datasetService.create(datasetData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() });
    },
  });
}

export function useUpdateDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      datasetId,
      data,
    }: {
      datasetId: string;
      data: Partial<DatasetCreate>;
    }) => datasetService.update(datasetId, data),
    onSuccess: (_, { datasetId }) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(datasetId) });
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() });
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datasetId: string) => datasetService.delete(datasetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() });
    },
  });
}

export function useScanDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      datasetId,
      request,
    }: {
      datasetId: string;
      request: DatasetScanRequest;
    }) => datasetService.scan(datasetId, request),
    onSuccess: (_, { datasetId }) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(datasetId) });
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() });
    },
  });
}

export function usePrepareDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      datasetId,
      outputDirectory,
    }: {
      datasetId: string;
      outputDirectory?: string;
    }) => datasetService.prepare(datasetId, outputDirectory),
    onSuccess: (_, { datasetId }) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(datasetId) });
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() });
    },
  });
}
