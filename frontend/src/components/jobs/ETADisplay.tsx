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
  // Additional context for better status messages
  totalFrames?: number | null;
  processedFrames?: number | null;
  currentStageName?: string | null;
  /** Estimate confidence: 'calculating' | 'estimated' | 'accurate' */
  confidence?: 'calculating' | 'estimated' | 'accurate';
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

/**
 * Get a friendly message for the current state when ETA is not yet available
 */
function getEstimatingMessage(
  currentStageName?: string | null,
  totalFrames?: number | null,
  processedFrames?: number | null,
  framesPerSecond?: number | null
): string {
  // If we have frames per second, we should have ETA - this is a fallback
  if (framesPerSecond && framesPerSecond > 0) {
    return 'Finalizing estimate...';
  }

  // If we know total frames but haven't started processing
  if (totalFrames && (!processedFrames || processedFrames === 0)) {
    const stageName = currentStageName ? STAGE_INFO[currentStageName as PipelineStage]?.name || currentStageName : 'extraction';
    return `Starting ${stageName}...`;
  }

  // If we're processing but don't have a rate yet
  if (processedFrames && processedFrames > 0 && totalFrames) {
    const percent = Math.round((processedFrames / totalFrames) * 100);
    return `Processing... (${percent}% complete)`;
  }

  // Early stages - just starting
  if (currentStageName) {
    const stageName = STAGE_INFO[currentStageName as PipelineStage]?.name || currentStageName;
    return `Starting ${stageName}...`;
  }

  return 'Initializing...';
}

/**
 * Get confidence indicator
 */
function ConfidenceIndicator({ confidence }: { confidence: 'calculating' | 'estimated' | 'accurate' }) {
  const config = {
    calculating: { color: 'text-yellow-500', label: 'Calculating', dot: 'bg-yellow-500 animate-pulse' },
    estimated: { color: 'text-blue-400', label: 'Estimated', dot: 'bg-blue-400' },
    accurate: { color: 'text-green-400', label: 'Based on current rate', dot: 'bg-green-400' },
  };

  const { color, label, dot } = config[confidence];

  return (
    <div className={`flex items-center gap-1.5 text-xs ${color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </div>
  );
}

export function ETADisplay({
  totalEta,
  stageEtas = [],
  framesPerSecond,
  compact = false,
  totalFrames,
  processedFrames,
  currentStageName,
  confidence,
}: ETADisplayProps) {
  // Determine confidence if not provided
  const effectiveConfidence = confidence || (
    framesPerSecond && framesPerSecond > 0 ? 'accurate' :
    totalEta !== null && totalEta !== undefined ? 'estimated' :
    'calculating'
  );

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

  const hasEta = totalEta !== null && totalEta !== undefined;
  const hasRate = framesPerSecond !== null && framesPerSecond !== undefined && framesPerSecond > 0;

  return (
    <div className="space-y-4">
      {/* Total ETA and Processing Rate */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${hasEta ? 'bg-primary-500/10' : 'bg-secondary-700/50'}`}>
            <ClockIcon className={`w-5 h-5 ${hasEta ? 'text-primary-400' : 'text-secondary-400 animate-pulse'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-secondary-400">Estimated Time</span>
              {hasEta && <ConfidenceIndicator confidence={effectiveConfidence} />}
            </div>
            <div className="text-lg font-semibold text-secondary-100">
              {hasEta
                ? `${formatDuration(totalEta)} remaining`
                : getEstimatingMessage(currentStageName, totalFrames, processedFrames, framesPerSecond)}
            </div>
          </div>
        </div>

        <div className="text-right">
          {hasRate ? (
            <>
              <span className="text-sm text-secondary-400">Processing Rate</span>
              <div className="text-lg font-semibold text-secondary-100">
                {framesPerSecond.toFixed(1)} frames/sec
              </div>
            </>
          ) : totalFrames ? (
            <>
              <span className="text-sm text-secondary-400">Total Frames</span>
              <div className="text-lg font-semibold text-secondary-100">
                {processedFrames ? `${processedFrames} / ` : ''}{totalFrames}
              </div>
            </>
          ) : null}
        </div>
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
                          <span className="animate-pulse">measuring rate...</span>
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
