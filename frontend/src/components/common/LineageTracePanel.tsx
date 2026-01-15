/**
 * Pipeline One - LineageTracePanel component
 * Shows clickable lineage path from raw data to current entity
 */

import { Link } from 'react-router-dom';
import {
  FolderIcon,
  CubeIcon,
  CogIcon,
  CheckCircleIcon,
  DocumentArrowDownIcon,
  ChevronRightIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline';

export interface LineageStage {
  type: 'raw' | 'dataset' | 'job' | 'curated' | 'training';
  id?: string;
  name: string;
  subtitle?: string;
  link?: string;
  isCurrent?: boolean;
}

interface LineageTracePanelProps {
  stages: LineageStage[];
  variant?: 'horizontal' | 'vertical' | 'compact';
  showIcons?: boolean;
  className?: string;
}

const stageConfig: Record<LineageStage['type'], { icon: typeof FolderIcon; color: string; label: string }> = {
  raw: {
    icon: FolderIcon,
    color: 'text-amber-400',
    label: 'Raw Data',
  },
  dataset: {
    icon: CubeIcon,
    color: 'text-blue-400',
    label: 'Dataset',
  },
  job: {
    icon: CogIcon,
    color: 'text-purple-400',
    label: 'Processing Job',
  },
  curated: {
    icon: CheckCircleIcon,
    color: 'text-green-400',
    label: 'Curated Set',
  },
  training: {
    icon: DocumentArrowDownIcon,
    color: 'text-primary-400',
    label: 'Training Export',
  },
};

export function LineageTracePanel({
  stages,
  variant = 'horizontal',
  showIcons = true,
  className = '',
}: LineageTracePanelProps) {
  if (variant === 'compact') {
    return <LineageTracePanelCompact stages={stages} className={className} />;
  }

  if (variant === 'vertical') {
    return <LineageTracePanelVertical stages={stages} showIcons={showIcons} className={className} />;
  }

  return (
    <div className={`flex items-center gap-2 flex-wrap ${className}`}>
      {stages.map((stage, index) => {
        const config = stageConfig[stage.type];
        const IconComponent = config.icon;
        const isLast = index === stages.length - 1;

        const content = (
          <div
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg transition-colors
              ${stage.isCurrent
                ? 'bg-primary-900/30 border border-primary-500'
                : stage.link
                  ? 'bg-secondary-800 hover:bg-secondary-700 cursor-pointer'
                  : 'bg-secondary-800/50'
              }
            `}
          >
            {showIcons && (
              <IconComponent className={`w-4 h-4 ${config.color}`} />
            )}
            <div className="flex flex-col">
              <span className={`text-sm font-medium ${stage.isCurrent ? 'text-primary-100' : 'text-secondary-200'}`}>
                {stage.name}
              </span>
              {stage.subtitle && (
                <span className="text-xs text-secondary-500">{stage.subtitle}</span>
              )}
            </div>
            {stage.link && !stage.isCurrent && (
              <ArrowTopRightOnSquareIcon className="w-3 h-3 text-secondary-500" />
            )}
          </div>
        );

        return (
          <div key={`${stage.type}-${stage.id || index}`} className="flex items-center gap-2">
            {stage.link && !stage.isCurrent ? (
              <Link to={stage.link}>{content}</Link>
            ) : (
              content
            )}
            {!isLast && (
              <ChevronRightIcon className="w-4 h-4 text-secondary-600" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function LineageTracePanelVertical({
  stages,
  showIcons,
  className,
}: {
  stages: LineageStage[];
  showIcons: boolean;
  className: string;
}) {
  return (
    <div className={`space-y-1 ${className}`}>
      {stages.map((stage, index) => {
        const config = stageConfig[stage.type];
        const IconComponent = config.icon;
        const isLast = index === stages.length - 1;

        const content = (
          <div className="flex items-start gap-3">
            {/* Timeline indicator */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  ${stage.isCurrent
                    ? 'bg-primary-500'
                    : 'bg-secondary-700'
                  }
                `}
              >
                {showIcons && (
                  <IconComponent
                    className={`w-4 h-4 ${stage.isCurrent ? 'text-white' : config.color}`}
                  />
                )}
              </div>
              {!isLast && (
                <div className="w-0.5 h-8 bg-secondary-700" />
              )}
            </div>

            {/* Content */}
            <div
              className={`
                flex-1 pb-4
                ${stage.link && !stage.isCurrent ? 'cursor-pointer group' : ''}
              `}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs text-secondary-500 uppercase tracking-wider">
                  {config.label}
                </span>
                {stage.isCurrent && (
                  <span className="text-xs px-1.5 py-0.5 bg-primary-500/20 text-primary-300 rounded">
                    Current
                  </span>
                )}
              </div>
              <p
                className={`
                  text-sm font-medium mt-0.5
                  ${stage.isCurrent
                    ? 'text-primary-100'
                    : stage.link
                      ? 'text-secondary-200 group-hover:text-primary-300'
                      : 'text-secondary-300'
                  }
                `}
              >
                {stage.name}
              </p>
              {stage.subtitle && (
                <p className="text-xs text-secondary-500 mt-0.5">{stage.subtitle}</p>
              )}
            </div>
          </div>
        );

        return stage.link && !stage.isCurrent ? (
          <Link key={`${stage.type}-${stage.id || index}`} to={stage.link}>
            {content}
          </Link>
        ) : (
          <div key={`${stage.type}-${stage.id || index}`}>{content}</div>
        );
      })}
    </div>
  );
}

function LineageTracePanelCompact({
  stages,
  className,
}: {
  stages: LineageStage[];
  className: string;
}) {
  return (
    <div className={`flex items-center gap-1 text-xs ${className}`}>
      {stages.map((stage, index) => {
        const config = stageConfig[stage.type];
        const IconComponent = config.icon;
        const isLast = index === stages.length - 1;

        const content = (
          <span
            className={`
              inline-flex items-center gap-1
              ${stage.isCurrent
                ? 'text-primary-300 font-medium'
                : stage.link
                  ? 'text-secondary-400 hover:text-primary-300'
                  : 'text-secondary-500'
              }
            `}
          >
            <IconComponent className={`w-3 h-3 ${config.color}`} />
            {stage.name}
          </span>
        );

        return (
          <span key={`${stage.type}-${stage.id || index}`} className="inline-flex items-center gap-1">
            {stage.link && !stage.isCurrent ? (
              <Link to={stage.link}>{content}</Link>
            ) : (
              content
            )}
            {!isLast && (
              <ChevronRightIcon className="w-3 h-3 text-secondary-600" />
            )}
          </span>
        );
      })}
    </div>
  );
}

// Helper function to build lineage stages from API response
export function buildLineageStages(lineage: {
  raw_data_path?: string;
  dataset?: { id: string; name: string };
  job?: { id: string; name: string };
  curated_dataset?: { id: string; name: string; version: number };
  training_dataset?: { id: string; name: string };
  current: 'dataset' | 'job' | 'curated' | 'training';
}): LineageStage[] {
  const stages: LineageStage[] = [];

  if (lineage.raw_data_path) {
    stages.push({
      type: 'raw',
      name: lineage.raw_data_path.split('/').slice(-2).join('/'),
      subtitle: 'Data Lake',
      isCurrent: false,
    });
  }

  if (lineage.dataset) {
    stages.push({
      type: 'dataset',
      id: lineage.dataset.id,
      name: lineage.dataset.name,
      link: `/datasets/${lineage.dataset.id}`,
      isCurrent: lineage.current === 'dataset',
    });
  }

  if (lineage.job) {
    stages.push({
      type: 'job',
      id: lineage.job.id,
      name: lineage.job.name,
      link: `/jobs/${lineage.job.id}`,
      isCurrent: lineage.current === 'job',
    });
  }

  if (lineage.curated_dataset) {
    stages.push({
      type: 'curated',
      id: lineage.curated_dataset.id,
      name: lineage.curated_dataset.name,
      subtitle: `v${lineage.curated_dataset.version}`,
      link: `/curated-datasets/${lineage.curated_dataset.id}`,
      isCurrent: lineage.current === 'curated',
    });
  }

  if (lineage.training_dataset) {
    stages.push({
      type: 'training',
      id: lineage.training_dataset.id,
      name: lineage.training_dataset.name,
      link: `/training-datasets/${lineage.training_dataset.id}`,
      isCurrent: lineage.current === 'training',
    });
  }

  return stages;
}
