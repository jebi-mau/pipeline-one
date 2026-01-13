/**
 * WorkflowPipeline - Visual representation of the SVO2 → Training Dataset pipeline
 */

import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  FolderPlusIcon,
  FilmIcon,
  CpuChipIcon,
  ArrowPathIcon,
  TagIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';

export interface WorkflowStage {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: 'pending' | 'available' | 'in_progress' | 'completed';
  href: string;
  actionLabel?: string;
  stats?: {
    label: string;
    value: string | number;
  };
}

interface WorkflowPipelineProps {
  stages: WorkflowStage[];
  orientation?: 'horizontal' | 'vertical';
  onStageAction?: (stageId: string) => void;
}

const statusColors = {
  pending: 'bg-secondary-700 border-secondary-600 text-secondary-400',
  available: 'bg-secondary-700 border-primary-500 text-primary-400',
  in_progress: 'bg-primary-900/30 border-primary-500 text-primary-400 animate-pulse',
  completed: 'bg-green-900/30 border-green-500 text-green-400',
};

const statusIcons = {
  pending: null,
  available: PlayIcon,
  in_progress: ArrowPathIcon,
  completed: CheckCircleIcon,
};

export function WorkflowPipeline({
  stages,
  orientation = 'horizontal',
  onStageAction,
}: WorkflowPipelineProps) {
  const isHorizontal = orientation === 'horizontal';

  return (
    <div
      className={clsx(
        'flex gap-4',
        isHorizontal ? 'flex-row overflow-x-auto pb-4' : 'flex-col'
      )}
    >
      {stages.map((stage, index) => {
        const StatusIcon = statusIcons[stage.status];
        const isClickable = stage.status !== 'pending';

        return (
          <div key={stage.id} className="flex items-center">
            {/* Stage Card */}
            <div
              className={clsx(
                'relative flex flex-col p-4 rounded-lg border-2 transition-all min-w-[200px]',
                statusColors[stage.status],
                isClickable && 'hover:scale-105 cursor-pointer'
              )}
            >
              {/* Status Badge */}
              {StatusIcon && (
                <div className="absolute -top-2 -right-2">
                  <StatusIcon
                    className={clsx(
                      'w-6 h-6',
                      stage.status === 'completed' && 'text-green-400',
                      stage.status === 'in_progress' && 'text-primary-400 animate-spin',
                      stage.status === 'available' && 'text-primary-400'
                    )}
                  />
                </div>
              )}

              {/* Stage Number */}
              <div className="absolute -top-3 -left-3 w-6 h-6 rounded-full bg-secondary-800 border border-secondary-600 flex items-center justify-center">
                <span className="text-xs font-bold text-secondary-300">
                  {index + 1}
                </span>
              </div>

              {/* Icon */}
              <div className="flex items-center justify-center mb-3">
                <stage.icon className="w-10 h-10" />
              </div>

              {/* Content */}
              <h3 className="font-semibold text-center mb-1">{stage.name}</h3>
              <p className="text-xs text-center text-secondary-400 mb-3">
                {stage.description}
              </p>

              {/* Stats */}
              {stage.stats && (
                <div className="text-center mb-3 py-2 bg-secondary-800/50 rounded">
                  <span className="text-lg font-bold">{stage.stats.value}</span>
                  <span className="text-xs block text-secondary-400">
                    {stage.stats.label}
                  </span>
                </div>
              )}

              {/* Action Button */}
              {isClickable && (
                <Link
                  to={stage.href}
                  className={clsx(
                    'mt-auto py-2 px-3 rounded text-xs font-medium text-center transition-colors',
                    stage.status === 'available' &&
                      'bg-primary-600 hover:bg-primary-500 text-white',
                    stage.status === 'in_progress' &&
                      'bg-primary-600/50 text-primary-200',
                    stage.status === 'completed' &&
                      'bg-green-600/30 hover:bg-green-600/50 text-green-300'
                  )}
                  onClick={(e) => {
                    if (onStageAction) {
                      e.preventDefault();
                      onStageAction(stage.id);
                    }
                  }}
                >
                  {stage.actionLabel ||
                    (stage.status === 'completed' ? 'View Results' : 'Start')}
                </Link>
              )}
            </div>

            {/* Connector Arrow */}
            {index < stages.length - 1 && (
              <div
                className={clsx(
                  'flex items-center justify-center',
                  isHorizontal ? 'px-2' : 'py-2 rotate-90'
                )}
              >
                <svg
                  className="w-8 h-8 text-secondary-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 7l5 5m0 0l-5 5m5-5H6"
                  />
                </svg>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Default workflow stages for the SVO2 → Training Dataset pipeline
export const defaultWorkflowStages: Omit<WorkflowStage, 'status' | 'stats'>[] = [
  {
    id: 'import',
    name: 'Import SVO2',
    description: 'Create dataset & import SVO2 files',
    icon: FolderPlusIcon,
    href: '/datasets',
    actionLabel: 'Create Dataset',
  },
  {
    id: 'extract',
    name: 'Extract Frames',
    description: 'Extract images, depth & sensor data',
    icon: FilmIcon,
    href: '/jobs',
    actionLabel: 'Run Extraction',
  },
  {
    id: 'segment',
    name: 'Segment Objects',
    description: 'Run SAM3 object detection',
    icon: CpuChipIcon,
    href: '/jobs',
    actionLabel: 'Run Segmentation',
  },
  {
    id: 'track',
    name: 'Track Objects',
    description: 'Track objects across frames',
    icon: ArrowPathIcon,
    href: '/jobs',
    actionLabel: 'Run Tracking',
  },
  {
    id: 'annotate',
    name: 'Review Annotations',
    description: 'Import & review annotations',
    icon: TagIcon,
    href: '/data',
    actionLabel: 'Review Data',
  },
  {
    id: 'export',
    name: 'Export Training Data',
    description: 'Export KITTI format dataset',
    icon: ArrowDownTrayIcon,
    href: '/data',
    actionLabel: 'Export Dataset',
  },
];
