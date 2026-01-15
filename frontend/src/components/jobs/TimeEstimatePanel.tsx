/**
 * Pipeline One - Pre-job Time Estimate Panel
 *
 * Displays estimated processing time before a job starts,
 * with per-stage breakdown and confidence indicator.
 */

import { ClockIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { LoadingSpinner } from '../common/LoadingSpinner';
import type { EstimateDurationResponse, EstimateConfidence, PipelineStage } from '../../types';
import { STAGE_INFO } from '../../types/job';

interface TimeEstimatePanelProps {
  /** Estimate data from API */
  estimate: EstimateDurationResponse | undefined;
  /** Whether estimate is loading */
  isLoading: boolean;
  /** Whether there's an error */
  isError?: boolean;
  /** Error message */
  error?: Error | null;
  /** Total frames from selected files (for display) */
  totalFrames?: number;
  /** Current frame skip setting (for comparison suggestions) */
  frameSkip?: number;
  /** Callback when user clicks a suggested frame skip */
  onFrameSkipSuggestion?: (skip: number) => void;
  /** Whether to show in compact mode */
  compact?: boolean;
}

function ConfidenceBadge({ confidence }: { confidence: EstimateConfidence }) {
  const config = {
    low: {
      bg: 'bg-yellow-900/30',
      text: 'text-yellow-400',
      border: 'border-yellow-600/50',
      label: 'Estimate',
      tooltip: 'Based on default benchmarks (no historical data)',
    },
    medium: {
      bg: 'bg-blue-900/30',
      text: 'text-blue-400',
      border: 'border-blue-600/50',
      label: 'Likely',
      tooltip: 'Based on limited historical data',
    },
    high: {
      bg: 'bg-green-900/30',
      text: 'text-green-400',
      border: 'border-green-600/50',
      label: 'Accurate',
      tooltip: 'Based on multiple completed jobs',
    },
  }[confidence];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.text} border ${config.border}`}
      title={config.tooltip}
    >
      {config.label}
    </span>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return '< 1 min';
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `~${hours}h ${minutes}m`;
  }
  return `~${minutes}m`;
}

export function TimeEstimatePanel({
  estimate,
  isLoading,
  isError,
  error,
  totalFrames,
  frameSkip = 1,
  onFrameSkipSuggestion,
  compact = false,
}: TimeEstimatePanelProps) {
  // Don't show anything if no files selected yet
  if (!isLoading && !estimate && !isError) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-3 bg-secondary-800/50 rounded-lg border border-secondary-700">
        <LoadingSpinner size="sm" />
        <span className="text-sm text-secondary-400">Calculating estimated time...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-3 bg-red-900/20 border border-red-600/30 rounded-lg">
        <p className="text-sm text-red-400">
          Could not calculate estimate: {error?.message || 'Unknown error'}
        </p>
      </div>
    );
  }

  if (!estimate) {
    return null;
  }

  // Calculate suggestions for reducing time
  const suggestedSkips: { skip: number; time: string; reduction: string }[] = [];
  if (onFrameSkipSuggestion && frameSkip <= 5 && estimate.estimated_duration_seconds > 300) {
    // Suggest higher frame skips to reduce time
    const baseTime = estimate.estimated_duration_seconds;
    [5, 10, 15].forEach((skip) => {
      if (skip > frameSkip) {
        const estimatedTime = Math.round(baseTime * (frameSkip / skip));
        const reduction = Math.round((1 - frameSkip / skip) * 100);
        suggestedSkips.push({
          skip,
          time: formatDuration(estimatedTime),
          reduction: `${reduction}%`,
        });
      }
    });
  }

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-2 bg-secondary-800/50 rounded-lg border border-secondary-700">
        <ClockIcon className="w-5 h-5 text-primary-400 flex-shrink-0" />
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-secondary-200">
            {estimate.estimated_duration_formatted}
          </span>
          <ConfidenceBadge confidence={estimate.confidence} />
        </div>
        <span className="text-xs text-secondary-500">
          ({estimate.estimated_total_frames.toLocaleString()} frames)
        </span>
      </div>
    );
  }

  return (
    <div className="p-4 bg-secondary-800/50 rounded-lg border border-secondary-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ClockIcon className="w-5 h-5 text-primary-400" />
          <span className="text-sm font-medium text-secondary-200">Estimated Processing Time</span>
        </div>
        <ConfidenceBadge confidence={estimate.confidence} />
      </div>

      {/* Main estimate */}
      <div className="mb-4">
        <div className="text-2xl font-bold text-primary-300">
          {estimate.estimated_duration_formatted}
        </div>
        <div className="text-xs text-secondary-500 mt-1">
          {estimate.estimated_total_frames.toLocaleString()} frames to process
          {totalFrames && totalFrames !== estimate.estimated_total_frames && (
            <span className="text-secondary-600">
              {' '}(from {totalFrames.toLocaleString()} total)
            </span>
          )}
        </div>
      </div>

      {/* Stage breakdown */}
      <div className="space-y-2 mb-4">
        <div className="text-xs font-medium text-secondary-400">Breakdown by stage:</div>
        <div className="grid gap-1.5">
          {Object.entries(estimate.breakdown).map(([stage, data]) => {
            const stageInfo = STAGE_INFO[stage as PipelineStage];
            const percent = Math.round(
              (data.estimated_seconds / estimate.estimated_duration_seconds) * 100
            );

            return (
              <div key={stage} className="flex items-center justify-between text-xs">
                <span className="text-secondary-400">
                  {stageInfo?.name || stage}
                </span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-secondary-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500/60 rounded-full"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <span className="text-secondary-500 w-12 text-right">
                    {formatDuration(data.estimated_seconds)}
                  </span>
                  <span className="text-secondary-600 w-14 text-right">
                    {data.fps.toFixed(1)} fps
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Frame skip suggestions */}
      {suggestedSkips.length > 0 && (
        <div className="pt-3 border-t border-secondary-700">
          <div className="flex items-start gap-2 mb-2">
            <InformationCircleIcon className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <span className="text-xs text-secondary-400">
              Increase frame skip to reduce processing time:
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestedSkips.map(({ skip, time, reduction }) => (
              <button
                key={skip}
                onClick={() => onFrameSkipSuggestion?.(skip)}
                className="px-2 py-1 text-xs bg-secondary-700 hover:bg-secondary-600 text-secondary-300 rounded transition-colors"
              >
                Skip {skip} = {time}{' '}
                <span className="text-green-400">(-{reduction})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Historical data info */}
      {estimate.based_on_jobs > 0 && (
        <div className="mt-3 pt-3 border-t border-secondary-700">
          <p className="text-xs text-secondary-600">
            Based on {estimate.based_on_jobs} previous job{estimate.based_on_jobs !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  );
}
