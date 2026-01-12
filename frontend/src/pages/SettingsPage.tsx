/**
 * Shalom - Settings page with state management
 */

import { useState, useEffect } from 'react';
import { useObjectClasses, useSystemConfig, useModelInfo } from '../hooks/useConfig';
import { useSettingsStore } from '../stores/settingsStore';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { AddClassModal } from '../components/settings/AddClassModal';
import { CheckIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';

export default function SettingsPage() {
  const { data: objectClasses, isLoading: classesLoading } = useObjectClasses();
  const { data: systemConfig, isLoading: configLoading } = useSystemConfig();
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo();

  const settings = useSettingsStore();

  const [isAddClassModalOpen, setIsAddClassModalOpen] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Local form state
  const [modelVariant, setModelVariant] = useState(settings.selectedModelVariant);
  const [precisionMode, setPrecisionMode] = useState(settings.precisionMode);
  const [confidenceThreshold, setConfidenceThreshold] = useState(settings.defaultConfidenceThreshold);
  const [batchSize, setBatchSize] = useState(settings.defaultBatchSize);

  // Sync from store on mount
  useEffect(() => {
    setModelVariant(settings.selectedModelVariant);
    setPrecisionMode(settings.precisionMode);
    setConfidenceThreshold(settings.defaultConfidenceThreshold);
    setBatchSize(settings.defaultBatchSize);
  }, [settings.selectedModelVariant, settings.precisionMode, settings.defaultConfidenceThreshold, settings.defaultBatchSize]);

  const handleSaveSettings = () => {
    settings.setSelectedModelVariant(modelVariant);
    settings.setPrecisionMode(precisionMode as 'fp32' | 'fp16' | 'bf16');
    settings.setDefaultConfidenceThreshold(confidenceThreshold);
    settings.setDefaultBatchSize(batchSize);

    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const hasChanges =
    modelVariant !== settings.selectedModelVariant ||
    precisionMode !== settings.precisionMode ||
    confidenceThreshold !== settings.defaultConfidenceThreshold ||
    batchSize !== settings.defaultBatchSize;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-secondary-100">Settings</h1>
        {saveSuccess && (
          <div className="flex items-center text-green-500 text-sm">
            <CheckIcon className="w-4 h-4 mr-1" />
            Settings saved
          </div>
        )}
      </div>

      {/* SAM 3 Configuration */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-secondary-100">
            SAM 3 Configuration
          </h2>
          <button
            onClick={handleSaveSettings}
            disabled={!hasChanges}
            className={`btn-primary text-sm ${!hasChanges ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            Save Changes
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="label">Model Variant</label>
            <select
              className="input"
              value={modelVariant}
              onChange={(e) => setModelVariant(e.target.value)}
            >
              <option value="sam3_hiera_tiny">SAM3 Tiny (~400MB, 4GB VRAM)</option>
              <option value="sam3_hiera_small">SAM3 Small (~900MB, 8GB VRAM)</option>
              <option value="sam3_hiera_base">SAM3 Base (~1.8GB, 12GB VRAM)</option>
              <option value="sam3_hiera_large">SAM3 Large (~2.4GB, 16GB VRAM)</option>
            </select>
          </div>
          <div>
            <label className="label">Precision Mode</label>
            <select
              className="input"
              value={precisionMode}
              onChange={(e) => setPrecisionMode(e.target.value as 'fp32' | 'fp16' | 'bf16')}
            >
              <option value="fp32">FP32 (Full Precision)</option>
              <option value="fp16">FP16 (Half Precision)</option>
              <option value="bf16">BF16 (Brain Float)</option>
            </select>
          </div>
          <div>
            <label className="label">Default Confidence Threshold</label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="0"
                max="100"
                value={confidenceThreshold * 100}
                onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value) / 100)}
                className="flex-1"
              />
              <span className="text-sm text-secondary-100 w-12 text-right">
                {confidenceThreshold.toFixed(2)}
              </span>
            </div>
          </div>
          <div>
            <label className="label">Default Batch Size</label>
            <input
              type="number"
              value={batchSize}
              onChange={(e) => setBatchSize(parseInt(e.target.value) || 1)}
              min="1"
              max="32"
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Object Classes */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-secondary-100">
            Object Classes
          </h2>
          <button
            onClick={() => setIsAddClassModalOpen(true)}
            className="btn-secondary text-sm"
          >
            <PlusIcon className="w-4 h-4 mr-1" />
            Add Custom Class
          </button>
        </div>
        <p className="text-secondary-400 mb-4">
          Configure preset and custom object classes for detection.
        </p>
        {classesLoading ? (
          <div className="flex justify-center py-4">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="space-y-2">
            {objectClasses?.map((cls) => (
              <div
                key={cls.name}
                className="flex items-center justify-between py-3 px-4 bg-secondary-700 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: cls.color }}
                  />
                  <span className="text-secondary-100 font-medium">{cls.name}</span>
                  {cls.kitti_type && (
                    <span className="text-xs text-secondary-400">({cls.kitti_type})</span>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-secondary-500 bg-secondary-800 px-2 py-1 rounded">
                    {cls.is_preset ? 'Preset' : 'Custom'}
                  </span>
                  {!cls.is_preset && (
                    <button className="text-red-400 hover:text-red-300 p-1">
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            {(!objectClasses || objectClasses.length === 0) && (
              <p className="text-secondary-400 text-center py-4">No object classes configured</p>
            )}
          </div>
        )}
      </div>

      {/* Data Paths */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">Data Paths</h2>
        {configLoading ? (
          <div className="flex justify-center py-4">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="label">SVO2 Directory</label>
              <input
                type="text"
                className="input bg-secondary-900"
                value={systemConfig?.svo2_directory || '/home/atlas/dev/pipe1/svo2_data'}
                readOnly
              />
            </div>
            <div>
              <label className="label">Output Directory</label>
              <input
                type="text"
                className="input bg-secondary-900"
                value={systemConfig?.output_directory || '/home/atlas/dev/pipe1/data/output'}
                readOnly
              />
            </div>
            <div>
              <label className="label">Models Directory</label>
              <input
                type="text"
                className="input bg-secondary-900"
                value={systemConfig?.models_directory || '/home/atlas/dev/pipe1/data/models'}
                readOnly
              />
            </div>
          </div>
        )}
      </div>

      {/* System Info */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">System Info</h2>
        {modelLoading ? (
          <div className="flex justify-center py-4">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-secondary-400">GPU:</span>
              <span className="ml-2 text-secondary-100">
                {modelInfo?.gpu_name || 'NVIDIA GeForce RTX 5090'}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">VRAM:</span>
              <span className="ml-2 text-secondary-100">
                {modelInfo?.gpu_vram_gb ? `${modelInfo.gpu_vram_gb} GB` : '32 GB'}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">GPU Available:</span>
              <span className={`ml-2 ${modelInfo?.gpu_available ? 'text-green-500' : 'text-red-500'}`}>
                {modelInfo?.gpu_available ? 'Yes' : 'No'}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">Loaded Model:</span>
              <span className="ml-2 text-secondary-100">
                {modelInfo?.loaded_model || 'None'}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">CUDA Version:</span>
              <span className="ml-2 text-secondary-100">
                {modelInfo?.cuda_version || '12.6'}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">ZED SDK:</span>
              <span className="ml-2 text-secondary-100">
                {systemConfig?.zed_sdk_version || '5.1'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Add Class Modal */}
      <AddClassModal
        isOpen={isAddClassModalOpen}
        onClose={() => setIsAddClassModalOpen(false)}
      />
    </div>
  );
}
