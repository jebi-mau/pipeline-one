/**
 * Shalom - Configuration hooks using React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configService } from '../services';
import type { ObjectClassCreate, PresetCreate } from '../types';

export const configKeys = {
  system: ['config', 'system'] as const,
  modelInfo: ['config', 'model-info'] as const,
  objectClasses: ['config', 'object-classes'] as const,
  presets: ['config', 'presets'] as const,
};

export function useSystemConfig() {
  return useQuery({
    queryKey: configKeys.system,
    queryFn: configService.getSystemConfig,
    staleTime: 60000, // Consider fresh for 1 minute
  });
}

export function useModelInfo() {
  return useQuery({
    queryKey: configKeys.modelInfo,
    queryFn: configService.getModelInfo,
    staleTime: 60000,
  });
}

export function useObjectClasses(includeCustom = true) {
  return useQuery({
    queryKey: [...configKeys.objectClasses, { includeCustom }],
    queryFn: () => configService.listObjectClasses(includeCustom),
  });
}

export function useCreateObjectClass() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ObjectClassCreate) => configService.createObjectClass(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: configKeys.objectClasses });
    },
  });
}

export function useDeleteObjectClass() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (classId: string) => configService.deleteObjectClass(classId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: configKeys.objectClasses });
    },
  });
}

export function usePresets() {
  return useQuery({
    queryKey: configKeys.presets,
    queryFn: configService.listPresets,
  });
}

export function useCreatePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PresetCreate) => configService.createPreset(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: configKeys.presets });
    },
  });
}

export function useDeletePreset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (presetId: string) => configService.deletePreset(presetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: configKeys.presets });
    },
  });
}
