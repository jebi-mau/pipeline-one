/**
 * Shalom - Settings store using Zustand with persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  // SAM3 Config
  selectedModelVariant: string;
  precisionMode: 'fp32' | 'fp16' | 'bf16';
  defaultConfidenceThreshold: number;
  defaultBatchSize: number;
  defaultFrameSkip: number;
  enableTracking: boolean;
  export3dData: boolean;

  // Actions
  setSelectedModelVariant: (variant: string) => void;
  setPrecisionMode: (mode: 'fp32' | 'fp16' | 'bf16') => void;
  setDefaultConfidenceThreshold: (threshold: number) => void;
  setDefaultBatchSize: (size: number) => void;
  setDefaultFrameSkip: (skip: number) => void;
  setEnableTracking: (enable: boolean) => void;
  setExport3dData: (enable: boolean) => void;
  resetToDefaults: () => void;
}

const defaultSettings = {
  selectedModelVariant: 'sam3_hiera_large',
  precisionMode: 'fp16' as const,
  defaultConfidenceThreshold: 0.5,
  defaultBatchSize: 8,
  defaultFrameSkip: 1,
  enableTracking: true,
  export3dData: true,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultSettings,

      setSelectedModelVariant: (variant) => set({ selectedModelVariant: variant }),
      setPrecisionMode: (mode) => set({ precisionMode: mode }),
      setDefaultConfidenceThreshold: (threshold) => set({ defaultConfidenceThreshold: threshold }),
      setDefaultBatchSize: (size) => set({ defaultBatchSize: size }),
      setDefaultFrameSkip: (skip) => set({ defaultFrameSkip: skip }),
      setEnableTracking: (enable) => set({ enableTracking: enable }),
      setExport3dData: (enable) => set({ export3dData: enable }),
      resetToDefaults: () => set(defaultSettings),
    }),
    {
      name: 'svo2-sam3-settings',
    }
  )
);
