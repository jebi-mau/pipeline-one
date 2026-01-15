/**
 * Pipeline One - ModelSelector component
 * Card-based UI for selecting SAM3 model variants
 */

import { useMemo } from 'react';
import {
  CheckIcon,
  CpuChipIcon,
  BoltIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { HelpIcon } from '../common/HelpIcon';
import { JOB_TOOLTIPS } from '../../constants/tooltips';

interface ModelInfo {
  name: string;
  size_mb: number;
  vram_required_gb: number;
  recommended_for: string;
}

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModel: string;
  onSelect: (modelName: string) => void;
  gpuName?: string;
  gpuVramGb?: number;
  defaultModel?: string;
}

// Model display configuration
const MODEL_CONFIG: Record<string, {
  displayName: string;
  shortName: string;
  qualityRating: number; // 1-4
  speedRating: number; // 1-4
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}> = {
  sam3_hiera_tiny: {
    displayName: 'SAM3 Tiny',
    shortName: 'Tiny',
    qualityRating: 1,
    speedRating: 4,
    icon: BoltIcon,
    color: 'text-green-400',
  },
  sam3_hiera_small: {
    displayName: 'SAM3 Small',
    shortName: 'Small',
    qualityRating: 2,
    speedRating: 3,
    icon: CpuChipIcon,
    color: 'text-blue-400',
  },
  sam3_hiera_base: {
    displayName: 'SAM3 Base',
    shortName: 'Base',
    qualityRating: 3,
    speedRating: 2,
    icon: CpuChipIcon,
    color: 'text-purple-400',
  },
  sam3_hiera_large: {
    displayName: 'SAM3 Large',
    shortName: 'Large',
    qualityRating: 4,
    speedRating: 1,
    icon: SparklesIcon,
    color: 'text-amber-400',
  },
};

function RatingBar({
  rating,
  max = 4,
  label,
  color
}: {
  rating: number;
  max?: number;
  label: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-secondary-500 w-12">{label}</span>
      <div className="flex gap-0.5">
        {Array.from({ length: max }).map((_, i) => (
          <div
            key={i}
            className={`w-3 h-1.5 rounded-sm ${
              i < rating ? color : 'bg-secondary-700'
            }`}
          />
        ))}
      </div>
    </div>
  );
}

export function ModelSelector({
  models,
  selectedModel,
  onSelect,
  gpuName,
  gpuVramGb,
  defaultModel,
}: ModelSelectorProps) {
  // Check VRAM compatibility for each model
  const modelCompatibility = useMemo(() => {
    const compatibility: Record<string, { compatible: boolean; warning?: string }> = {};

    models.forEach((model) => {
      if (gpuVramGb !== undefined) {
        if (model.vram_required_gb > gpuVramGb) {
          compatibility[model.name] = {
            compatible: false,
            warning: `Requires ${model.vram_required_gb}GB VRAM, but your GPU has ${gpuVramGb}GB`,
          };
        } else if (model.vram_required_gb > gpuVramGb * 0.8) {
          compatibility[model.name] = {
            compatible: true,
            warning: `Uses ${Math.round((model.vram_required_gb / gpuVramGb) * 100)}% of available VRAM`,
          };
        } else {
          compatibility[model.name] = { compatible: true };
        }
      } else {
        compatibility[model.name] = { compatible: true };
      }
    });

    return compatibility;
  }, [models, gpuVramGb]);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <CpuChipIcon className="w-4 h-4 text-primary-400" />
        <span className="text-sm font-medium text-secondary-300">SAM3 Model</span>
        <HelpIcon
          content={
            <div className="space-y-2">
              <p className="font-medium">{JOB_TOOLTIPS.model.title}</p>
              <p>{JOB_TOOLTIPS.model.description}</p>
            </div>
          }
          position="right"
        />
        {gpuName && (
          <span className="ml-auto text-xs text-green-400">
            GPU: {gpuName}
          </span>
        )}
      </div>

      {/* Model Cards */}
      <div className="grid grid-cols-2 gap-3">
        {models.map((model) => {
          const config = MODEL_CONFIG[model.name] || {
            displayName: model.name,
            shortName: model.name.split('_').pop() || model.name,
            qualityRating: 2,
            speedRating: 2,
            icon: CpuChipIcon,
            color: 'text-secondary-400',
          };
          const isSelected = selectedModel === model.name;
          const isRecommended = defaultModel === model.name;
          const { compatible, warning } = modelCompatibility[model.name] || { compatible: true };
          const IconComponent = config.icon;

          return (
            <button
              key={model.name}
              onClick={() => onSelect(model.name)}
              disabled={!compatible}
              className={`
                relative p-3 rounded-lg border-2 text-left transition-all
                ${isSelected
                  ? 'bg-primary-900/30 border-primary-500'
                  : compatible
                    ? 'bg-secondary-800 border-secondary-700 hover:border-secondary-500'
                    : 'bg-secondary-800/50 border-secondary-700 opacity-60 cursor-not-allowed'
                }
              `}
            >
              {/* Recommended badge */}
              {isRecommended && (
                <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-primary-600 text-white text-xs rounded-full">
                  Recommended
                </span>
              )}

              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute top-2 right-2 w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                  <CheckIcon className="w-3 h-3 text-white" />
                </div>
              )}

              {/* Model header */}
              <div className="flex items-center gap-2 mb-2">
                <IconComponent className={`w-5 h-5 ${config.color}`} />
                <span className={`font-medium ${isSelected ? 'text-primary-100' : 'text-secondary-200'}`}>
                  {config.displayName}
                </span>
              </div>

              {/* Stats */}
              <div className="space-y-1.5 mb-2">
                <RatingBar
                  label="Quality"
                  rating={config.qualityRating}
                  color="bg-purple-500"
                />
                <RatingBar
                  label="Speed"
                  rating={config.speedRating}
                  color="bg-green-500"
                />
              </div>

              {/* Technical specs */}
              <div className="flex items-center gap-3 text-xs text-secondary-500">
                <span>{model.size_mb} MB</span>
                <span>{model.vram_required_gb} GB VRAM</span>
              </div>

              {/* Use case */}
              <p className="mt-2 text-xs text-secondary-400 line-clamp-1">
                {model.recommended_for}
              </p>

              {/* Warning */}
              {warning && (
                <div className={`mt-2 flex items-center gap-1 text-xs ${compatible ? 'text-yellow-500' : 'text-red-400'}`}>
                  <ExclamationTriangleIcon className="w-3 h-3" />
                  <span className="line-clamp-1">{warning}</span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected model detail */}
      {selectedModel && (
        <div className="p-2 bg-secondary-800/50 rounded-lg">
          <p className="text-xs text-secondary-400">
            <span className="text-secondary-300 font-medium">
              {MODEL_CONFIG[selectedModel]?.displayName || selectedModel}:
            </span>{' '}
            {models.find(m => m.name === selectedModel)?.recommended_for}
          </p>
        </div>
      )}
    </div>
  );
}

// Compact version for wizard steps
export function ModelSelectorCompact({
  models,
  selectedModel,
  onSelect,
  defaultModel,
}: Omit<ModelSelectorProps, 'gpuName' | 'gpuVramGb'>) {
  return (
    <div className="flex gap-2 flex-wrap">
      {models.map((model) => {
        const config = MODEL_CONFIG[model.name];
        const isSelected = selectedModel === model.name;
        const isRecommended = defaultModel === model.name;

        return (
          <button
            key={model.name}
            onClick={() => onSelect(model.name)}
            className={`
              relative px-3 py-2 rounded-lg border transition-all
              ${isSelected
                ? 'bg-primary-900/30 border-primary-500 text-primary-100'
                : 'bg-secondary-800 border-secondary-700 text-secondary-300 hover:border-secondary-500'
              }
            `}
          >
            <span className="font-medium">{config?.shortName || model.name}</span>
            {isRecommended && !isSelected && (
              <span className="ml-1 text-xs text-primary-400">(rec)</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
