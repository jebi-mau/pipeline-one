/**
 * Pipeline One - Configuration API service
 */

import api from './api';
import type {
  SystemConfig,
  ModelInfo,
  ObjectClass,
  ObjectClassCreate,
  Preset,
  PresetCreate,
} from '../types';

export const configService = {
  getSystemConfig: async (): Promise<SystemConfig> => {
    const { data } = await api.get('/config/system');
    return data;
  },

  getModelInfo: async (): Promise<ModelInfo> => {
    const { data } = await api.get('/config/model-info');
    return data;
  },

  // Object Classes
  listObjectClasses: async (includeCustom = true): Promise<ObjectClass[]> => {
    const { data } = await api.get('/config/object-classes', {
      params: { include_custom: includeCustom },
    });
    return data;
  },

  getObjectClass: async (classId: string): Promise<ObjectClass> => {
    const { data } = await api.get(`/config/object-classes/${classId}`);
    return data;
  },

  createObjectClass: async (objectClass: ObjectClassCreate): Promise<ObjectClass> => {
    const { data } = await api.post('/config/object-classes', objectClass);
    return data;
  },

  deleteObjectClass: async (classId: string): Promise<void> => {
    await api.delete(`/config/object-classes/${classId}`);
  },

  // Presets
  listPresets: async (): Promise<Preset[]> => {
    const { data } = await api.get('/config/presets');
    return data;
  },

  getPreset: async (presetId: string): Promise<Preset> => {
    const { data } = await api.get(`/config/presets/${presetId}`);
    return data;
  },

  createPreset: async (preset: PresetCreate): Promise<Preset> => {
    const { data } = await api.post('/config/presets', preset);
    return data;
  },

  deletePreset: async (presetId: string): Promise<void> => {
    await api.delete(`/config/presets/${presetId}`);
  },
};
