/**
 * Pipeline One - PresetSelector component
 * Visual cards for quick job configuration presets
 */

import { useState } from 'react';
import {
  BoltIcon,
  ScaleIcon,
  SparklesIcon,
  Cog6ToothIcon,
  BookmarkIcon,
} from '@heroicons/react/24/outline';
import { CheckIcon } from '@heroicons/react/24/solid';
import type { PipelineStage } from '../../types/job';

// Preset configuration interface
export interface JobPreset {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  isBuiltIn: boolean;
  config: {
    sam3_model_variant: string;
    sam3_confidence_threshold: number;
    sam3_iou_threshold: number;
    sam3_batch_size: number;
    frame_skip: number;
    enable_tracking: boolean;
    export_3d_data: boolean;
    enable_diversity_filter: boolean;
    diversity_similarity_threshold: number;
    diversity_motion_threshold: number;
    stages_to_run: PipelineStage[];
  };
}

// Built-in presets
export const BUILT_IN_PRESETS: JobPreset[] = [
  {
    id: 'quick',
    name: 'Quick Processing',
    description: 'Fast preview with basic detection. Good for testing or large datasets.',
    icon: BoltIcon,
    color: 'from-green-500 to-emerald-600',
    isBuiltIn: true,
    config: {
      sam3_model_variant: 'sam3_hiera_tiny',
      sam3_confidence_threshold: 0.5,
      sam3_iou_threshold: 0.7,
      sam3_batch_size: 8,
      frame_skip: 3,
      enable_tracking: false,
      export_3d_data: false,
      enable_diversity_filter: false,
      diversity_similarity_threshold: 0.85,
      diversity_motion_threshold: 0.02,
      stages_to_run: ['extraction', 'segmentation'],
    },
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Good quality with reasonable speed. Recommended for most use cases.',
    icon: ScaleIcon,
    color: 'from-blue-500 to-indigo-600',
    isBuiltIn: true,
    config: {
      sam3_model_variant: 'sam3_hiera_small',
      sam3_confidence_threshold: 0.5,
      sam3_iou_threshold: 0.7,
      sam3_batch_size: 4,
      frame_skip: 1,
      enable_tracking: true,
      export_3d_data: true,
      enable_diversity_filter: true,
      diversity_similarity_threshold: 0.85,
      diversity_motion_threshold: 0.02,
      stages_to_run: ['extraction', 'segmentation', 'reconstruction', 'tracking'],
    },
  },
  {
    id: 'high-quality',
    name: 'High Quality',
    description: 'Best accuracy for production datasets. Slower but most complete.',
    icon: SparklesIcon,
    color: 'from-purple-500 to-pink-600',
    isBuiltIn: true,
    config: {
      sam3_model_variant: 'sam3_hiera_large',
      sam3_confidence_threshold: 0.4,
      sam3_iou_threshold: 0.5,
      sam3_batch_size: 2,
      frame_skip: 0,
      enable_tracking: true,
      export_3d_data: true,
      enable_diversity_filter: false,
      diversity_similarity_threshold: 0.85,
      diversity_motion_threshold: 0.02,
      stages_to_run: ['extraction', 'segmentation', 'reconstruction', 'tracking'],
    },
  },
];

interface PresetSelectorProps {
  onSelect: (preset: JobPreset) => void;
  selectedPresetId?: string | null;
  savedPresets?: JobPreset[];
  onCustomize?: () => void;
  showSavedPresets?: boolean;
}

export function PresetSelector({
  onSelect,
  selectedPresetId,
  savedPresets = [],
  onCustomize,
  showSavedPresets = true,
}: PresetSelectorProps) {
  const [showAllPresets, setShowAllPresets] = useState(false);

  const allPresets = showSavedPresets
    ? [...BUILT_IN_PRESETS, ...savedPresets]
    : BUILT_IN_PRESETS;

  const displayedPresets = showAllPresets
    ? allPresets
    : allPresets.slice(0, 3);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-secondary-300">Quick Start Presets</span>
        {savedPresets.length > 0 && (
          <button
            onClick={() => setShowAllPresets(!showAllPresets)}
            className="text-xs text-primary-400 hover:text-primary-300"
          >
            {showAllPresets ? 'Show less' : `Show all (${allPresets.length})`}
          </button>
        )}
      </div>

      {/* Preset Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {displayedPresets.map((preset) => {
          const isSelected = selectedPresetId === preset.id;
          const IconComponent = preset.icon;

          return (
            <button
              key={preset.id}
              onClick={() => onSelect(preset)}
              className={`
                relative p-4 rounded-xl border-2 text-left transition-all
                ${isSelected
                  ? 'bg-gradient-to-br ' + preset.color + ' border-transparent'
                  : 'bg-secondary-800 border-secondary-700 hover:border-secondary-500'
                }
              `}
            >
              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute top-2 right-2 w-5 h-5 bg-white/20 rounded-full flex items-center justify-center">
                  <CheckIcon className="w-3 h-3 text-white" />
                </div>
              )}

              {/* Bookmark for saved presets */}
              {!preset.isBuiltIn && (
                <BookmarkIcon className="absolute top-2 right-2 w-4 h-4 text-secondary-500" />
              )}

              {/* Icon */}
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                isSelected ? 'bg-white/20' : 'bg-secondary-700'
              }`}>
                <IconComponent className={`w-6 h-6 ${isSelected ? 'text-white' : 'text-secondary-300'}`} />
              </div>

              {/* Content */}
              <h3 className={`font-medium mb-1 ${isSelected ? 'text-white' : 'text-secondary-200'}`}>
                {preset.name}
              </h3>
              <p className={`text-xs line-clamp-2 ${isSelected ? 'text-white/80' : 'text-secondary-500'}`}>
                {preset.description}
              </p>

              {/* Quick stats */}
              <div className={`mt-3 flex flex-wrap gap-1.5 text-xs ${isSelected ? 'text-white/70' : 'text-secondary-500'}`}>
                <span className="px-1.5 py-0.5 rounded bg-black/20">
                  {preset.config.sam3_model_variant.replace('sam3_hiera_', '')}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-black/20">
                  skip {preset.config.frame_skip}
                </span>
                {preset.config.enable_diversity_filter && (
                  <span className="px-1.5 py-0.5 rounded bg-black/20">
                    diversity
                  </span>
                )}
              </div>
            </button>
          );
        })}

        {/* Custom option */}
        {onCustomize && (
          <button
            onClick={onCustomize}
            className="p-4 rounded-xl border-2 border-dashed border-secondary-700 hover:border-secondary-500 text-left transition-all group"
          >
            <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 bg-secondary-800 group-hover:bg-secondary-700">
              <Cog6ToothIcon className="w-6 h-6 text-secondary-400" />
            </div>
            <h3 className="font-medium mb-1 text-secondary-300">Custom</h3>
            <p className="text-xs text-secondary-500">
              Configure all settings manually
            </p>
          </button>
        )}
      </div>
    </div>
  );
}

// Compact version for inline use
export function PresetSelectorCompact({
  onSelect,
  selectedPresetId,
}: Pick<PresetSelectorProps, 'onSelect' | 'selectedPresetId'>) {
  return (
    <div className="flex gap-2">
      {BUILT_IN_PRESETS.map((preset) => {
        const isSelected = selectedPresetId === preset.id;
        const IconComponent = preset.icon;

        return (
          <button
            key={preset.id}
            onClick={() => onSelect(preset)}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg border transition-all
              ${isSelected
                ? 'bg-primary-900/30 border-primary-500 text-primary-100'
                : 'bg-secondary-800 border-secondary-700 text-secondary-300 hover:border-secondary-500'
              }
            `}
          >
            <IconComponent className="w-4 h-4" />
            <span className="text-sm font-medium">{preset.name}</span>
          </button>
        );
      })}
    </div>
  );
}

// Hook to manage preset selection and customization
interface UsePresetReturn {
  selectedPreset: JobPreset | null;
  selectPreset: (preset: JobPreset) => void;
  applyPreset: (preset: JobPreset) => JobPreset['config'];
  isUsingPreset: boolean;
}

export function usePreset(initialPresetId?: string): UsePresetReturn {
  const [selectedPreset, setSelectedPreset] = useState<JobPreset | null>(() => {
    if (initialPresetId) {
      return BUILT_IN_PRESETS.find(p => p.id === initialPresetId) || null;
    }
    return BUILT_IN_PRESETS[1]; // Default to Balanced
  });

  const selectPreset = (preset: JobPreset) => {
    setSelectedPreset(preset);
  };

  const applyPreset = (preset: JobPreset): JobPreset['config'] => {
    return { ...preset.config };
  };

  return {
    selectedPreset,
    selectPreset,
    applyPreset,
    isUsingPreset: selectedPreset !== null,
  };
}
