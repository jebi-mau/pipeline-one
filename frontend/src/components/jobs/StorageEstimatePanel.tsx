/**
 * Pipeline One - Pre-job Storage Estimate Panel
 *
 * Displays estimated storage requirements before a job starts,
 * with warnings if disk space is low.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  CircleStackIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { storageService } from '../../services/storageService';
import type { EstimateStorageResponse, PipelineStage } from '../../types/job';

interface StorageEstimatePanelProps {
  /** Total frames to process */
  totalFrames: number;
  /** Selected pipeline stages */
  stagesToRun: PipelineStage[];
  /** Frame skip setting */
  frameSkip: number;
  /** Whether to extract point clouds */
  extractPointClouds?: boolean;
  /** Whether to extract right camera image */
  extractRightImage?: boolean;
  /** Whether to extract segmentation masks */
  extractMasks?: boolean;
  /** Image format */
  imageFormat?: string;
  /** Whether to show in compact mode */
  compact?: boolean;
}

export function StorageEstimatePanel({
  totalFrames,
  stagesToRun,
  frameSkip,
  extractPointClouds = true,
  extractRightImage = true,
  extractMasks = true,
  imageFormat = 'png',
  compact = false,
}: StorageEstimatePanelProps) {
  const [estimate, setEstimate] = useState<EstimateStorageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEstimate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await storageService.estimateJobStorage({
        total_frames: totalFrames,
        stages_to_run: stagesToRun,
        frame_skip: frameSkip,
        extract_point_clouds: extractPointClouds,
        extract_right_image: extractRightImage,
        extract_masks: extractMasks,
        image_format: imageFormat,
      });
      setEstimate(result);
    } catch (err) {
      setError('Failed to estimate storage');
      console.error('Storage estimation failed:', err);
    } finally {
      setLoading(false);
    }
  }, [totalFrames, stagesToRun, frameSkip, extractPointClouds, extractRightImage, extractMasks, imageFormat]);

  useEffect(() => {
    if (totalFrames > 0 && stagesToRun.length > 0) {
      loadEstimate();
    }
  }, [totalFrames, stagesToRun, frameSkip, extractPointClouds, extractRightImage, extractMasks, imageFormat, loadEstimate]);

  // Don't show anything if no frames
  if (totalFrames <= 0) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-3 bg-secondary-800/50 rounded-lg border border-secondary-700">
        <LoadingSpinner size="sm" />
        <span className="text-sm text-secondary-400">Estimating storage...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 bg-red-900/20 border border-red-600/30 rounded-lg">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  if (!estimate) {
    return null;
  }

  // Determine status icon and colors
  const getStatusIndicator = () => {
    if (!estimate.sufficient_space) {
      return {
        Icon: ExclamationCircleIcon,
        iconColor: 'text-red-400',
        bgColor: 'bg-red-900/20',
        borderColor: 'border-red-600/30',
      };
    }
    if (estimate.warning) {
      return {
        Icon: ExclamationTriangleIcon,
        iconColor: 'text-yellow-400',
        bgColor: 'bg-yellow-900/20',
        borderColor: 'border-yellow-600/30',
      };
    }
    return {
      Icon: CheckCircleIcon,
      iconColor: 'text-green-400',
      bgColor: 'bg-secondary-800/50',
      borderColor: 'border-secondary-700',
    };
  };

  const { Icon, iconColor, bgColor, borderColor } = getStatusIndicator();

  if (compact) {
    return (
      <div className={`flex items-center gap-3 p-2 rounded-lg border ${bgColor} ${borderColor}`}>
        <CircleStackIcon className={`w-5 h-5 ${iconColor} flex-shrink-0`} />
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-secondary-200">
            {estimate.estimated_formatted}
          </span>
          {!estimate.sufficient_space && (
            <span className="text-xs text-red-400">(insufficient space)</span>
          )}
        </div>
        <span className="text-xs text-secondary-500">
          / {estimate.available_formatted} free
        </span>
      </div>
    );
  }

  return (
    <div className={`p-4 rounded-lg border ${bgColor} ${borderColor}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CircleStackIcon className="w-5 h-5 text-primary-400" />
          <span className="text-sm font-medium text-secondary-200">Estimated Storage</span>
        </div>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>

      {/* Main estimate */}
      <div className="mb-4">
        <div className="text-2xl font-bold text-primary-300">
          {estimate.estimated_formatted}
        </div>
        <div className="text-xs text-secondary-500 mt-1">
          {estimate.details.frames_to_process.toLocaleString()} frames to extract
        </div>
      </div>

      {/* Available space */}
      <div className="flex items-center justify-between text-sm mb-3">
        <span className="text-secondary-400">Available disk space:</span>
        <span className={estimate.sufficient_space ? 'text-green-400' : 'text-red-400'}>
          {estimate.available_formatted}
        </span>
      </div>

      {/* Warning message */}
      {estimate.warning && (
        <div
          className={`p-3 rounded-lg flex items-start gap-2 ${
            !estimate.sufficient_space
              ? 'bg-red-900/30 border border-red-600/30'
              : 'bg-yellow-900/30 border border-yellow-600/30'
          }`}
        >
          {!estimate.sufficient_space ? (
            <ExclamationCircleIcon className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          ) : (
            <ExclamationTriangleIcon className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
          )}
          <span
            className={`text-xs ${
              !estimate.sufficient_space ? 'text-red-300' : 'text-yellow-300'
            }`}
          >
            {estimate.warning}
          </span>
        </div>
      )}

      {/* Estimation breakdown */}
      <div className="mt-3 pt-3 border-t border-secondary-700">
        <div className="text-xs text-secondary-500 space-y-1">
          <div className="flex justify-between">
            <span>Stages:</span>
            <span className="text-secondary-400">
              {estimate.details.stages.join(', ')}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Point Clouds:</span>
            <span className="text-secondary-400">
              {estimate.details.extract_point_clouds ? 'Yes (~10MB/frame)' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Right Camera:</span>
            <span className="text-secondary-400">
              {estimate.details.extract_right_image ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Masks:</span>
            <span className="text-secondary-400">
              {estimate.details.extract_masks ? 'Yes (~5MB/frame)' : 'No'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
