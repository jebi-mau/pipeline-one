/**
 * Pipeline One - Configuration type definitions
 */

export interface ObjectClass {
  id: string;
  name: string;
  prompt: string;
  color: string;
  kitti_type: string | null;
  is_preset: boolean;
  created_at: string;
}

export interface ObjectClassCreate {
  name: string;
  prompt: string;
  color: string;
  kitti_type?: string;
}

export interface PresetConfig {
  object_class_ids: string[];
  sam3_model_variant: string;
  sam3_confidence_threshold: number;
  sam3_iou_threshold: number;
  sam3_batch_size: number;
  frame_skip: number;
  enable_tracking: boolean;
}

export interface Preset {
  id: string;
  name: string;
  description: string | null;
  config: PresetConfig;
  created_at: string;
}

export interface PresetCreate {
  name: string;
  description?: string;
  config: PresetConfig;
}

export interface ModelVariant {
  name: string;
  size_mb: number;
  vram_required_gb: number;
  recommended_for: string;
}

export interface ModelInfo {
  available_models: ModelVariant[];
  default_model: string;
  loaded_model: string | null;
  gpu_available: boolean;
  gpu_name: string | null;
  gpu_vram_gb: number | null;
  cuda_version: string | null;
}

export interface SystemConfig {
  app_name: string;
  app_version: string;
  environment: string;
  data_root: string;
  svo2_directory: string;
  output_directory: string;
  models_directory: string;
  zed_sdk_installed: boolean;
  sam3_model_loaded: boolean;
  gpu_available: boolean;
  max_workers: number;
  zed_sdk_version: string | null;
}
