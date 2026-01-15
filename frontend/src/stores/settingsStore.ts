/**
 * Pipeline One - Settings store using Zustand with persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { PipelineStage } from '../types/job';

// Job configuration preset interface
export interface SavedJobPreset {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  config: JobPresetConfig;
}

export interface JobPresetConfig {
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
}

// Last used job configuration
export interface LastUsedConfig {
  name?: string;
  config: Partial<JobPresetConfig>;
  timestamp: string;
}

interface SettingsState {
  // SAM3 Config (default settings)
  selectedModelVariant: string;
  precisionMode: 'fp32' | 'fp16' | 'bf16';
  defaultConfidenceThreshold: number;
  defaultBatchSize: number;
  defaultFrameSkip: number;
  enableTracking: boolean;
  export3dData: boolean;

  // Job presets
  savedPresets: SavedJobPreset[];
  lastUsedConfig: LastUsedConfig | null;

  // UI preferences
  preferWizardMode: boolean;

  // Actions - Default settings
  setSelectedModelVariant: (variant: string) => void;
  setPrecisionMode: (mode: 'fp32' | 'fp16' | 'bf16') => void;
  setDefaultConfidenceThreshold: (threshold: number) => void;
  setDefaultBatchSize: (size: number) => void;
  setDefaultFrameSkip: (skip: number) => void;
  setEnableTracking: (enable: boolean) => void;
  setExport3dData: (enable: boolean) => void;
  resetToDefaults: () => void;

  // Actions - Presets
  createPreset: (name: string, description: string, config: JobPresetConfig) => string;
  updatePreset: (id: string, updates: Partial<Omit<SavedJobPreset, 'id' | 'createdAt'>>) => void;
  deletePreset: (id: string) => void;
  getPreset: (id: string) => SavedJobPreset | undefined;

  // Actions - Last used config
  saveLastUsedConfig: (config: Partial<JobPresetConfig>, name?: string) => void;
  clearLastUsedConfig: () => void;

  // Actions - UI preferences
  setPreferWizardMode: (prefer: boolean) => void;
}

const defaultSettings = {
  selectedModelVariant: 'sam3_hiera_large',
  precisionMode: 'fp16' as const,
  defaultConfidenceThreshold: 0.5,
  defaultBatchSize: 8,
  defaultFrameSkip: 1,
  enableTracking: true,
  export3dData: true,
  savedPresets: [] as SavedJobPreset[],
  lastUsedConfig: null as LastUsedConfig | null,
  preferWizardMode: true,
};

// Generate unique ID for presets
function generatePresetId(): string {
  return `preset_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...defaultSettings,

      // Default settings actions
      setSelectedModelVariant: (variant) => set({ selectedModelVariant: variant }),
      setPrecisionMode: (mode) => set({ precisionMode: mode }),
      setDefaultConfidenceThreshold: (threshold) => set({ defaultConfidenceThreshold: threshold }),
      setDefaultBatchSize: (size) => set({ defaultBatchSize: size }),
      setDefaultFrameSkip: (skip) => set({ defaultFrameSkip: skip }),
      setEnableTracking: (enable) => set({ enableTracking: enable }),
      setExport3dData: (enable) => set({ export3dData: enable }),
      resetToDefaults: () => set({
        selectedModelVariant: defaultSettings.selectedModelVariant,
        precisionMode: defaultSettings.precisionMode,
        defaultConfidenceThreshold: defaultSettings.defaultConfidenceThreshold,
        defaultBatchSize: defaultSettings.defaultBatchSize,
        defaultFrameSkip: defaultSettings.defaultFrameSkip,
        enableTracking: defaultSettings.enableTracking,
        export3dData: defaultSettings.export3dData,
      }),

      // Preset actions
      createPreset: (name, description, config) => {
        const id = generatePresetId();
        const newPreset: SavedJobPreset = {
          id,
          name,
          description,
          createdAt: new Date().toISOString(),
          config,
        };
        set((state) => ({
          savedPresets: [...state.savedPresets, newPreset],
        }));
        return id;
      },

      updatePreset: (id, updates) => {
        set((state) => ({
          savedPresets: state.savedPresets.map((preset) =>
            preset.id === id ? { ...preset, ...updates } : preset
          ),
        }));
      },

      deletePreset: (id) => {
        set((state) => ({
          savedPresets: state.savedPresets.filter((preset) => preset.id !== id),
        }));
      },

      getPreset: (id) => {
        return get().savedPresets.find((preset) => preset.id === id);
      },

      // Last used config actions
      saveLastUsedConfig: (config, name) => {
        set({
          lastUsedConfig: {
            name,
            config,
            timestamp: new Date().toISOString(),
          },
        });
      },

      clearLastUsedConfig: () => {
        set({ lastUsedConfig: null });
      },

      // UI preference actions
      setPreferWizardMode: (prefer) => {
        set({ preferWizardMode: prefer });
      },
    }),
    {
      name: 'pipeline-one-settings',
    }
  )
);
