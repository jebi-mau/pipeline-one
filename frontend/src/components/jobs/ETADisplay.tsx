/**
 * ETA Display Component
 * Shows job time estimates with per-stage breakdown
 */

import { ClockIcon, PlayIcon, CheckCircleIcon, PauseIcon } from '@heroicons/react/24/outline';
import type { StageETA } from '../../types/job';
import { STAGE_INFO, type PipelineStage } from '../../types/job';

interface ETADisplayProps {
  totalEta: number | null | undefined;
  stageEtas?: StageETA[];
  framesPerSecond?: number | null;
  compact?: boolean;
}

/**
 * Format seconds into human-readable duration
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return '< 1 min';
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 24) {
    const days = Math.floor(hours / 24);
    return `~${days}d ${hours % 24}h`;
  }

  if (hours > 0) {
    return `~${hours}h ${minutes}m`;
  }

  return `~${minutes}m`;
}

/**
 * Get status icon for a stage
 */
function StageStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircleIcon className="w-4 h-4 text-green-500" />;
    case 'running':
      return <PlayIcon className="w-4 h-4 text-primary-500 animate-pulse" />;
    case 'skipped':
      return <PauseIcon className="w-4 h-4 text-secondary-500" />;
    default:
      return <ClockIcon className="w-4 h-4 text-secondary-500" />;
  }
}

/**
 * Get status color class
 */
function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'text-green-400';
    case 'running':
      return 'text-primary-400';
    case 'skipped':
      return 'text-secondary-500';
    default:
      return 'text-secondary-400';
  }
}

export function ETADisplay({
  totalEta,
  stageEtas = [],
  framesPerSecond,
  compact = false,
}: ETADisplayProps) {
  if (compact) {
    // Compact mode - just show total ETA
    if (totalEta === null || totalEta === undefined) {
      return <span className="text-secondary-500">--</span>;
    }
    return (
      <span className="text-secondary-300 flex items-center gap-1">
        <ClockIcon className="w-4 h-4" />
        {formatDuration(totalEta)}
      </span>
    );
  }

  return (
    <div className="space-y-4">
      {/* Total ETA and Processing Rate */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClockIcon className="w-5 h-5 text-primary-400" />
          <div>
            <span className="text-sm text-secondary-400">Estimated Time</span>
            <div className="text-lg font-semibold text-secondary-100">
              {totalEta !== null && totalEta !== undefined
                ? `${formatDuration(totalEta)} remaining`
                : 'Calculating...'}
            </div>
          </div>
        </div>

        {framesPerSecond !== null && framesPerSecond !== undefined && framesPerSecond > 0 && (
          <div className="text-right">
            <span className="text-sm text-secondary-400">Processing Rate</span>
            <div className="text-lg font-semibold text-secondary-100">
              {framesPerSecond.toFixed(1)} frames/sec
            </div>
          </div>
        )}
      </div>

      {/* Per-Stage Breakdown */}
      {stageEtas.length > 0 && (
        <div className="border-t border-secondary-700 pt-4">
          <h4 className="text-sm font-medium text-secondary-400 mb-3">Stage Breakdown</h4>
          <div className="space-y-2">
            {stageEtas.map((stage) => {
              const stageInfo = STAGE_INFO[stage.stage as PipelineStage];
              const stageName = stageInfo?.name || stage.stage;

              return (
                <div
                  key={stage.stage}
                  className="flex items-center justify-between py-1"
                >
                  <div className="flex items-center gap-2">
                    <StageStatusIcon status={stage.status} />
                    <span className={`text-sm ${getStatusColor(stage.status)}`}>
                      {stage.stage_number}. {stageName}
                    </span>
                  </div>
                  <div className="text-sm">
                    {stage.status === 'completed' && stage.elapsed_seconds !== null && (
                      <span className="text-green-400">
                        {formatDuration(stage.elapsed_seconds)}
                      </span>
                    )}
                    {stage.status === 'running' && (
                      <span className="text-primary-400">
                        {stage.elapsed_seconds !== null && (
                          <span className="text-secondary-500 mr-2">
                            {formatDuration(stage.elapsed_seconds)} elapsed
                          </span>
                        )}
                        {stage.eta_seconds !== null ? (
                          <span>{formatDuration(stage.eta_seconds)} left</span>
                        ) : (
                          <span>calculating...</span>
                        )}
                      </span>
                    )}
                    {stage.status === 'pending' && stage.eta_seconds !== null && (
                      <span className="text-secondary-500">
                        ~{formatDuration(stage.eta_seconds)}
                      </span>
                    )}
                    {stage.status === 'pending' && stage.eta_seconds === null && (
                      <span className="text-secondary-600">--</span>
                    )}
                    {stage.status === 'skipped' && (
                      <span className="text-secondary-600">skipped</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ETADisplay;
