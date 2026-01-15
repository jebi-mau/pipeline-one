/**
 * Pipeline One - Pre-job duration estimation hook
 *
 * Uses React Query with debouncing to fetch estimated processing time
 * when job configuration changes.
 */

import { useQuery } from '@tanstack/react-query';
import { useState, useEffect, useMemo, useCallback } from 'react';
import { jobsService, filesService } from '../services';
import type { EstimateDurationRequest, EstimateDurationResponse, PipelineStage } from '../types';

// Query keys
export const estimateKeys = {
  all: ['estimates'] as const,
  duration: (params: EstimateDurationRequest) => [...estimateKeys.all, 'duration', params] as const,
  frameCount: (paths: string[]) => [...estimateKeys.all, 'frameCount', paths] as const,
};

interface UseJobEstimateOptions {
  /** Paths to SVO2 files */
  svo2Files: string[];
  /** Frame skip setting (default: 1) */
  frameSkip?: number;
  /** SAM3 model variant (default: sam3_hiera_large) */
  modelVariant?: string;
  /** Pipeline stages to run */
  stagesToRun?: PipelineStage[];
  /** Debounce delay in ms (default: 500) */
  debounceMs?: number;
  /** Whether to enable the query */
  enabled?: boolean;
}

interface UseJobEstimateResult {
  /** Estimation data */
  estimate: EstimateDurationResponse | undefined;
  /** Whether estimate is loading */
  isLoading: boolean;
  /** Whether there's an error */
  isError: boolean;
  /** Error message if any */
  error: Error | null;
  /** Total frame count from files */
  totalFrames: number | undefined;
  /** Whether frame count is loading */
  isLoadingFrames: boolean;
  /** Refetch estimate */
  refetch: () => void;
}

/**
 * Hook to estimate job duration before starting.
 *
 * Automatically fetches frame counts from SVO2 files and uses benchmarks
 * to estimate processing time. Debounces requests to avoid excessive API calls.
 */
export function useJobEstimate({
  svo2Files,
  frameSkip = 1,
  modelVariant = 'sam3_hiera_large',
  stagesToRun = ['extraction', 'segmentation', 'reconstruction', 'tracking'],
  debounceMs = 500,
  enabled = true,
}: UseJobEstimateOptions): UseJobEstimateResult {
  // Track debounced request parameters
  const [debouncedParams, setDebouncedParams] = useState<EstimateDurationRequest | null>(null);

  // Memoize request params
  const requestParams = useMemo(
    () => ({
      svo2_files: svo2Files,
      frame_skip: frameSkip,
      sam3_model_variant: modelVariant,
      stages_to_run: stagesToRun,
    }),
    [svo2Files, frameSkip, modelVariant, stagesToRun]
  );

  // Debounce parameter changes
  useEffect(() => {
    if (!enabled || svo2Files.length === 0) {
      setDebouncedParams(null);
      return;
    }

    const timer = setTimeout(() => {
      setDebouncedParams(requestParams);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [requestParams, enabled, svo2Files.length, debounceMs]);

  // Fetch frame counts first (for display purposes)
  const {
    data: frameCountData,
    isLoading: isLoadingFrames,
  } = useQuery({
    queryKey: estimateKeys.frameCount(svo2Files),
    queryFn: () => filesService.getFrameCount(svo2Files),
    enabled: enabled && svo2Files.length > 0,
    staleTime: 60000, // Frame counts don't change - cache for 1 minute
  });

  // Fetch estimate (uses server-side frame counting)
  const {
    data: estimate,
    isLoading: isLoadingEstimate,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: estimateKeys.duration(debouncedParams || requestParams),
    queryFn: () => jobsService.estimateDuration(debouncedParams!),
    enabled: enabled && !!debouncedParams && svo2Files.length > 0,
    staleTime: 30000, // Cache estimates for 30 seconds
    retry: 1,
  });

  const handleRefetch = useCallback(() => {
    refetch();
  }, [refetch]);

  return {
    estimate,
    isLoading: isLoadingEstimate || (enabled && svo2Files.length > 0 && !debouncedParams),
    isError,
    error: error as Error | null,
    totalFrames: frameCountData?.total_frames,
    isLoadingFrames,
    refetch: handleRefetch,
  };
}
