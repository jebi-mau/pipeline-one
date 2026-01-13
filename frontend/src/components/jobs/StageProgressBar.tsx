/**
 * Pipeline One - Stage Progress Bar component
 * Shows pipeline stages with visual progress indicator
 */

import { CheckCircleIcon } from '@heroicons/react/24/solid';
import type { PipelineStage } from '../../types/job';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';

interface StageProgressBarProps {
  stages: PipelineStage[];
  currentStage: number;
  currentStageName?: string | null;
  progress: number;
  processedFrames?: number | null;
  totalFrames?: number | null;
  compact?: boolean;
  jobStatus?: string;
}

export function StageProgressBar({
  stages,
  currentStage,
  currentStageName,
  progress,
  processedFrames,
  totalFrames,
  compact = false,
  jobStatus,
}: StageProgressBarProps) {
  // Default to all stages if none specified
  const selectedStages = stages.length > 0 ? stages : ALL_PIPELINE_STAGES;

  // Get stage status: 'completed' | 'active' | 'pending' | 'skipped'
  const getStageStatus = (stage: PipelineStage): 'completed' | 'active' | 'pending' | 'skipped' => {
    const stageNumber = STAGE_INFO[stage].number;

    if (!selectedStages.includes(stage)) {
      return 'skipped';
    }

    // If job is completed, all selected stages are completed
    if (jobStatus === 'completed') {
      return 'completed';
    }

    if (stageNumber < currentStage) {
      return 'completed';
    }

    if (stageNumber === currentStage) {
      return 'active';
    }

    return 'pending';
  };

  if (compact) {
    // Compact version for job list table
    return (
      <div className="space-y-1">
        <div className="flex items-center space-x-1">
          {selectedStages.map((stage, idx) => {
            const status = getStageStatus(stage);
            const info = STAGE_INFO[stage];

            return (
              <div key={stage} className="flex items-center">
                <div
                  className={`w-6 h-1.5 rounded-full transition-colors ${
                    status === 'completed'
                      ? 'bg-green-500'
                      : status === 'active'
                      ? 'bg-primary-500'
                      : 'bg-secondary-700'
                  }`}
                  title={`${info.name}: ${status}`}
                />
                {idx < selectedStages.length - 1 && (
                  <div className="w-1" />
                )}
              </div>
            );
          })}
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-secondary-400">
            {currentStageName || 'Pending'}
          </span>
          <span className="text-xs text-secondary-400">
            {progress.toFixed(1)}%
          </span>
        </div>
      </div>
    );
  }

  // Full version with labels
  return (
    <div className="space-y-3">
      {/* Stage pills */}
      <div className="flex items-center justify-between">
        {ALL_PIPELINE_STAGES.map((stage, idx) => {
          const status = getStageStatus(stage);
          const info = STAGE_INFO[stage];
          const isSelected = selectedStages.includes(stage);

          return (
            <div key={stage} className="flex items-center flex-1">
              {/* Stage indicator */}
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                    status === 'completed'
                      ? 'bg-green-500 text-white'
                      : status === 'active'
                      ? 'bg-primary-500 text-white animate-pulse'
                      : status === 'skipped'
                      ? 'bg-secondary-800 text-secondary-600'
                      : 'bg-secondary-700 text-secondary-400'
                  }`}
                >
                  {status === 'completed' ? (
                    <CheckCircleIcon className="w-5 h-5" />
                  ) : (
                    <span className="text-sm font-medium">{info.number}</span>
                  )}
                </div>
                <span
                  className={`mt-1 text-xs font-medium ${
                    status === 'completed'
                      ? 'text-green-400'
                      : status === 'active'
                      ? 'text-primary-400'
                      : status === 'skipped'
                      ? 'text-secondary-600 line-through'
                      : 'text-secondary-500'
                  }`}
                >
                  {info.name}
                </span>
                {!isSelected && (
                  <span className="text-xs text-secondary-600">(skipped)</span>
                )}
              </div>

              {/* Connector line */}
              {idx < ALL_PIPELINE_STAGES.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-2 transition-colors ${
                    status === 'completed' ? 'bg-green-500' : 'bg-secondary-700'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between text-xs text-secondary-400 mb-1">
          <span>
            {currentStageName
              ? `Stage ${currentStage}: ${currentStageName.charAt(0).toUpperCase() + currentStageName.slice(1)}`
              : 'Pending'}
          </span>
          <span>{progress.toFixed(1)}% complete</span>
        </div>
        <div className="w-full bg-secondary-700 rounded-full h-2">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        {totalFrames !== null && totalFrames !== undefined && (
          <div className="mt-1 text-xs text-secondary-500 text-right">
            {processedFrames?.toLocaleString() || 0} / {totalFrames.toLocaleString()} frames
          </div>
        )}
      </div>
    </div>
  );
}
