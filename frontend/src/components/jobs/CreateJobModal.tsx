/**
 * Shalom - Create Job Modal component with enhanced file browser and full configuration
 */

import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useBrowseFiles } from '../../hooks/useFiles';
import { useObjectClasses, useModelInfo } from '../../hooks/useConfig';
import { useCreateJob, useStartJob } from '../../hooks/useJobs';
import {
  FolderIcon,
  DocumentIcon,
  CheckIcon,
  HomeIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  CpuChipIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import type { PipelineStage } from '../../types/job';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';

interface CreateJobModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Quick access locations
const QUICK_LOCATIONS = [
  { name: 'Home', path: '/home/atlas', icon: HomeIcon },
  { name: 'SVO2 Data', path: '/home/atlas/dev/pipe1/data/svo2', icon: FolderIcon },
  { name: 'Project', path: '/home/atlas/dev/pipe1', icon: FolderIcon },
];

export function CreateJobModal({ isOpen, onClose }: CreateJobModalProps) {
  // Basic job settings
  const [jobName, setJobName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [autoStart, setAutoStart] = useState(true);

  // File browser state
  const [currentPath, setCurrentPath] = useState('/home/atlas/dev/pipe1/data/svo2');
  const [pathInput, setPathInput] = useState('/home/atlas/dev/pipe1/data/svo2');
  const [showAllFiles, setShowAllFiles] = useState(false);

  // Pipeline stage selection
  const [selectedStages, setSelectedStages] = useState<PipelineStage[]>([...ALL_PIPELINE_STAGES]);

  // Model and processing settings
  const [selectedModel, setSelectedModel] = useState('sam3_hiera_large');
  const [confidence, setConfidence] = useState(0.5);
  const [iouThreshold, setIouThreshold] = useState(0.7);
  const [batchSize, setBatchSize] = useState(4);
  const [frameSkip, setFrameSkip] = useState(1);
  const [enableTracking, setEnableTracking] = useState(true);
  const [export3DData, setExport3DData] = useState(true);

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: filesData, isLoading: filesLoading, isError, refetch } = useBrowseFiles(currentPath, showAllFiles);
  const { data: classesData, isLoading: classesLoading } = useObjectClasses();
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo();
  const createJob = useCreateJob();
  const startJob = useStartJob();

  // Sync path input when current path changes
  useEffect(() => {
    setPathInput(currentPath);
  }, [currentPath]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setJobName('');
      setSelectedFiles([]);
      setSelectedClasses([]);
      setAutoStart(true);
      setCurrentPath('/home/atlas/dev/pipe1/data/svo2');
      setSelectedStages([...ALL_PIPELINE_STAGES]);
      setSelectedModel('sam3_hiera_large');
      setConfidence(0.5);
      setIouThreshold(0.7);
      setBatchSize(4);
      setFrameSkip(1);
      setEnableTracking(true);
      setExport3DData(true);
      setShowAdvanced(false);
    }
  }, [isOpen]);

  // Set default model from API
  useEffect(() => {
    if (modelInfo?.default_model) {
      setSelectedModel(modelInfo.default_model);
    }
  }, [modelInfo]);

  const handleNavigate = useCallback((path: string) => {
    setCurrentPath(path);
  }, []);

  const handlePathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pathInput.trim()) {
      setCurrentPath(pathInput.trim());
    }
  };

  const handleGoUp = () => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    handleNavigate(parentPath);
  };

  const handleSelectFile = (filePath: string) => {
    setSelectedFiles(prev =>
      prev.includes(filePath)
        ? prev.filter(f => f !== filePath)
        : [...prev, filePath]
    );
  };

  const handleSelectClass = (className: string) => {
    setSelectedClasses(prev =>
      prev.includes(className)
        ? prev.filter(c => c !== className)
        : [...prev, className]
    );
  };

  const handleSelectAllClasses = () => {
    if (classesData) {
      const allNames = classesData.map(c => c.name);
      const allSelected = allNames.every(n => selectedClasses.includes(n));
      if (allSelected) {
        setSelectedClasses([]);
      } else {
        setSelectedClasses(allNames);
      }
    }
  };

  // Handle stage toggle with dependency management
  const handleToggleStage = (stage: PipelineStage) => {
    setSelectedStages(prev => {
      const isSelected = prev.includes(stage);

      if (isSelected) {
        // Removing a stage - also remove dependent stages
        const toRemove = new Set<PipelineStage>();
        toRemove.add(stage);

        // If removing extraction, remove all
        if (stage === 'extraction') {
          return [];
        }
        // If removing segmentation, remove reconstruction and tracking
        if (stage === 'segmentation') {
          toRemove.add('reconstruction');
          toRemove.add('tracking');
        }
        // If removing reconstruction, remove tracking
        if (stage === 'reconstruction') {
          toRemove.add('tracking');
        }

        return prev.filter(s => !toRemove.has(s));
      } else {
        // Adding a stage - also add required dependencies
        const toAdd = new Set<PipelineStage>([stage]);

        // Always require extraction
        toAdd.add('extraction');
        // If adding reconstruction or tracking, require segmentation
        if (stage === 'reconstruction' || stage === 'tracking') {
          toAdd.add('segmentation');
        }
        // If adding tracking, require reconstruction
        if (stage === 'tracking') {
          toAdd.add('reconstruction');
        }

        // Merge and maintain order
        return ALL_PIPELINE_STAGES.filter(s => prev.includes(s) || toAdd.has(s));
      }
    });
  };

  const handleSelectAllSvo2 = () => {
    if (filesData?.files) {
      const svo2Files = filesData.files
        .filter(f => f.name.toLowerCase().endsWith('.svo2'))
        .map(f => f.path);

      const allSelected = svo2Files.every(f => selectedFiles.includes(f));
      if (allSelected) {
        setSelectedFiles(prev => prev.filter(f => !svo2Files.includes(f)));
      } else {
        setSelectedFiles(prev => [...new Set([...prev, ...svo2Files])]);
      }
    }
  };

  const handleSubmit = async () => {
    if (!jobName.trim() || selectedFiles.length === 0 || selectedClasses.length === 0 || selectedStages.length === 0) {
      return;
    }

    try {
      const job = await createJob.mutateAsync({
        name: jobName,
        input_paths: selectedFiles,
        config: {
          object_class_ids: selectedClasses,
          sam3_model_variant: selectedModel,
          sam3_confidence_threshold: confidence,
          sam3_iou_threshold: iouThreshold,
          sam3_batch_size: batchSize,
          frame_skip: frameSkip,
          enable_tracking: enableTracking,
          export_3d_data: export3DData,
          stages_to_run: selectedStages,
        },
      });

      if (autoStart && job.id) {
        await startJob.mutateAsync(job.id);
      }

      onClose();
    } catch (error) {
      console.error('Failed to create job:', error);
    }
  };

  const isSubmitting = createJob.isPending || startJob.isPending;
  const canSubmit = jobName.trim() && selectedFiles.length > 0 && selectedClasses.length > 0 && selectedStages.length > 0 && !isSubmitting;

  // Parse path into breadcrumb segments
  const pathSegments = currentPath.split('/').filter(Boolean);

  // Get selected model info
  const selectedModelInfo = modelInfo?.available_models.find(m => m.name === selectedModel);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Job" size="xl">
      <div className="space-y-6 max-h-[80vh] overflow-y-auto pr-2">
        {/* Job Name */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            Job Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            placeholder="Enter job name..."
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* File Browser */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-secondary-300">
              Select SVO2 Files <span className="text-red-500">*</span> ({selectedFiles.length} selected)
            </label>
            <div className="flex items-center space-x-2">
              <label className="flex items-center text-xs text-secondary-400">
                <input
                  type="checkbox"
                  checked={showAllFiles}
                  onChange={(e) => setShowAllFiles(e.target.checked)}
                  className="w-3 h-3 mr-1 rounded border-secondary-700 bg-secondary-800 text-primary-600"
                />
                Show all files
              </label>
              {filesData?.files && filesData.files.some(f => f.name.toLowerCase().endsWith('.svo2')) && (
                <button
                  onClick={handleSelectAllSvo2}
                  className="text-xs text-primary-400 hover:text-primary-300"
                >
                  Select all SVO2
                </button>
              )}
            </div>
          </div>

          {/* Quick Access */}
          <div className="flex items-center space-x-2 mb-2">
            {QUICK_LOCATIONS.map((loc) => (
              <button
                key={loc.path}
                onClick={() => handleNavigate(loc.path)}
                className={`flex items-center px-2 py-1 text-xs rounded ${
                  currentPath === loc.path
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-700 text-secondary-300 hover:bg-secondary-600'
                }`}
              >
                <loc.icon className="w-3 h-3 mr-1" />
                {loc.name}
              </button>
            ))}
          </div>

          <div className="bg-secondary-800 border border-secondary-700 rounded-lg overflow-hidden">
            {/* Path Input */}
            <form onSubmit={handlePathSubmit} className="flex items-center border-b border-secondary-700">
              <input
                type="text"
                value={pathInput}
                onChange={(e) => setPathInput(e.target.value)}
                className="flex-1 px-3 py-2 bg-secondary-900 text-sm text-secondary-100 focus:outline-none"
                placeholder="Enter path..."
              />
              <button
                type="submit"
                className="px-3 py-2 bg-secondary-800 text-secondary-400 hover:text-secondary-100"
              >
                Go
              </button>
              <button
                type="button"
                onClick={() => refetch()}
                className="px-3 py-2 bg-secondary-800 text-secondary-400 hover:text-secondary-100"
                title="Refresh"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>
            </form>

            {/* Breadcrumb */}
            <div className="flex items-center px-3 py-1 bg-secondary-900/50 text-xs overflow-x-auto">
              <button
                onClick={() => handleNavigate('/')}
                className="text-secondary-400 hover:text-secondary-100"
              >
                /
              </button>
              {pathSegments.map((segment, index) => (
                <span key={index} className="flex items-center">
                  <ChevronRightIcon className="w-3 h-3 text-secondary-600 mx-1" />
                  <button
                    onClick={() => handleNavigate('/' + pathSegments.slice(0, index + 1).join('/'))}
                    className="text-secondary-400 hover:text-secondary-100"
                  >
                    {segment}
                  </button>
                </span>
              ))}
            </div>

            {/* File List */}
            <div className="max-h-40 overflow-y-auto">
              {filesLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : isError ? (
                <div className="px-3 py-8 text-center text-red-400 text-sm">
                  Error loading directory. Check if the path exists and is accessible.
                </div>
              ) : (
                <div className="divide-y divide-secondary-700">
                  {/* Go up button */}
                  {currentPath !== '/' && (
                    <button
                      onClick={handleGoUp}
                      className="w-full px-3 py-2 flex items-center space-x-2 hover:bg-secondary-700 text-left"
                    >
                      <FolderIcon className="w-4 h-4 text-yellow-500" />
                      <span className="text-secondary-300">..</span>
                      <span className="text-secondary-500 text-xs">(Go up)</span>
                    </button>
                  )}

                  {/* Directories */}
                  {filesData?.directories?.map((dir) => (
                    <button
                      key={dir.path}
                      onClick={() => handleNavigate(dir.path)}
                      className="w-full px-3 py-2 flex items-center space-x-2 hover:bg-secondary-700 text-left"
                    >
                      <FolderIcon className="w-4 h-4 text-yellow-500" />
                      <span className="text-secondary-300">{dir.name}</span>
                      <span className="text-secondary-500 text-xs">({dir.item_count} items)</span>
                    </button>
                  ))}

                  {/* Files */}
                  {filesData?.files?.map((file) => {
                    const isSvo2 = file.name.toLowerCase().endsWith('.svo2');
                    return (
                      <button
                        key={file.path}
                        onClick={() => isSvo2 && handleSelectFile(file.path)}
                        disabled={!isSvo2}
                        className={`w-full px-3 py-2 flex items-center justify-between text-left ${
                          isSvo2
                            ? selectedFiles.includes(file.path)
                              ? 'bg-primary-900/30 hover:bg-primary-900/40'
                              : 'hover:bg-secondary-700'
                            : 'opacity-50 cursor-not-allowed'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <DocumentIcon className={`w-4 h-4 ${isSvo2 ? 'text-blue-500' : 'text-secondary-500'}`} />
                          <span className={isSvo2 ? 'text-secondary-300' : 'text-secondary-500'}>{file.name}</span>
                          <span className="text-secondary-500 text-xs">
                            ({(file.size_bytes / 1024 / 1024).toFixed(1)} MB)
                          </span>
                        </div>
                        {isSvo2 && selectedFiles.includes(file.path) && (
                          <CheckIcon className="w-4 h-4 text-primary-500" />
                        )}
                      </button>
                    );
                  })}

                  {/* Empty state */}
                  {!filesData?.directories?.length && !filesData?.files?.length && (
                    <div className="px-3 py-8 text-center text-secondary-500 text-sm">
                      No files or directories found
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="mt-2 p-2 bg-secondary-900 rounded-lg">
              <div className="text-xs text-secondary-400 mb-1">Selected files:</div>
              <div className="flex flex-wrap gap-1">
                {selectedFiles.map((file) => (
                  <span
                    key={file}
                    className="inline-flex items-center px-2 py-0.5 bg-primary-900/50 text-primary-300 rounded text-xs"
                  >
                    {file.split('/').pop()}
                    <button
                      onClick={() => handleSelectFile(file)}
                      className="ml-1 text-primary-400 hover:text-primary-200"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Object Classes */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-secondary-300">
              Object Classes <span className="text-red-500">*</span> ({selectedClasses.length} selected)
            </label>
            {classesData && classesData.length > 0 && (
              <button
                onClick={handleSelectAllClasses}
                className="text-xs text-primary-400 hover:text-primary-300"
              >
                {selectedClasses.length === classesData.length ? 'Deselect all' : 'Select all'}
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {classesLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              classesData?.map((cls) => (
                <button
                  key={cls.name}
                  onClick={() => handleSelectClass(cls.name)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    selectedClasses.includes(cls.name)
                      ? 'bg-primary-600 text-white'
                      : 'bg-secondary-700 text-secondary-300 hover:bg-secondary-600'
                  }`}
                  style={selectedClasses.includes(cls.name) ? { backgroundColor: cls.color } : {}}
                >
                  {cls.name}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Pipeline Stages Selection */}
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <BeakerIcon className="w-4 h-4 text-primary-400" />
            <label className="block text-sm font-medium text-secondary-300">
              Pipeline Stages <span className="text-red-500">*</span> ({selectedStages.length} selected)
            </label>
          </div>
          <p className="text-xs text-secondary-500 mb-3">
            Select which processing stages to execute. Dependencies will be automatically added.
          </p>
          <div className="grid grid-cols-2 gap-2">
            {ALL_PIPELINE_STAGES.map((stage) => {
              const info = STAGE_INFO[stage];
              const isSelected = selectedStages.includes(stage);
              const isRequired = stage === 'extraction' && selectedStages.length > 0;

              return (
                <button
                  key={stage}
                  onClick={() => handleToggleStage(stage)}
                  className={`flex items-start p-3 rounded-lg border transition-colors text-left ${
                    isSelected
                      ? 'bg-primary-900/30 border-primary-600 text-primary-100'
                      : 'bg-secondary-800 border-secondary-700 text-secondary-400 hover:border-secondary-600'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 mr-3 mt-0.5 flex items-center justify-center flex-shrink-0 ${
                    isSelected
                      ? 'bg-primary-600 border-primary-600'
                      : 'border-secondary-600'
                  }`}>
                    {isSelected && <CheckIcon className="w-3 h-3 text-white" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <span className={`text-sm font-medium ${isSelected ? 'text-primary-100' : 'text-secondary-300'}`}>
                        {info.number}. {info.name}
                      </span>
                      {isRequired && (
                        <span className="ml-2 text-xs text-yellow-500">(required)</span>
                      )}
                    </div>
                    <p className="text-xs text-secondary-500 mt-0.5">{info.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
          {selectedStages.length === 0 && (
            <p className="mt-2 text-xs text-red-400">At least one stage must be selected</p>
          )}
        </div>

        {/* Model Selection */}
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <CpuChipIcon className="w-4 h-4 text-primary-400" />
            <label className="block text-sm font-medium text-secondary-300">
              SAM3 Model
            </label>
          </div>
          {modelLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <div className="space-y-2">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {modelInfo?.available_models.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name.replace('sam3_hiera_', 'SAM3 Hiera ').replace(/^\w/, c => c.toUpperCase())} - {model.recommended_for}
                  </option>
                ))}
              </select>
              {selectedModelInfo && (
                <div className="flex items-center space-x-4 text-xs text-secondary-500">
                  <span>Size: {selectedModelInfo.size_mb} MB</span>
                  <span>VRAM: {selectedModelInfo.vram_required_gb} GB</span>
                  {modelInfo?.gpu_name && (
                    <span className="text-green-500">GPU: {modelInfo.gpu_name}</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Basic Configuration */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <Cog6ToothIcon className="w-4 h-4 text-primary-400" />
            <label className="block text-sm font-medium text-secondary-300">
              Processing Settings
            </label>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-secondary-400 mb-1">
                Confidence Threshold
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-secondary-500">Min confidence for detections (0-1)</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary-400 mb-1">
                Frame Skip
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={frameSkip}
                onChange={(e) => setFrameSkip(parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-secondary-500">Process every Nth frame</p>
            </div>
          </div>
        </div>

        {/* Advanced Settings Toggle */}
        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center space-x-2 text-sm text-secondary-400 hover:text-secondary-200"
          >
            <ChevronDownIcon className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
            <span>Advanced Settings</span>
          </button>

          {showAdvanced && (
            <div className="mt-4 space-y-4 p-4 bg-secondary-800/50 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-secondary-400 mb-1">
                    IOU Threshold
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={iouThreshold}
                    onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="mt-1 text-xs text-secondary-500">Non-max suppression threshold</p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-secondary-400 mb-1">
                    Batch Size
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="16"
                    value={batchSize}
                    onChange={(e) => setBatchSize(parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <p className="mt-1 text-xs text-secondary-500">Frames per batch (adjust for VRAM)</p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableTracking}
                    onChange={(e) => setEnableTracking(e.target.checked)}
                    className="w-4 h-4 rounded border-secondary-700 bg-secondary-800 text-primary-600 focus:ring-primary-500"
                  />
                  <div>
                    <span className="text-sm text-secondary-300">Enable Object Tracking</span>
                    <p className="text-xs text-secondary-500">Track objects across frames using ByteTrack</p>
                  </div>
                </label>

                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={export3DData}
                    onChange={(e) => setExport3DData(e.target.checked)}
                    className="w-4 h-4 rounded border-secondary-700 bg-secondary-800 text-primary-600 focus:ring-primary-500"
                  />
                  <div>
                    <span className="text-sm text-secondary-300">Export 3D Data</span>
                    <p className="text-xs text-secondary-500">Generate 3D bounding boxes from depth data</p>
                  </div>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Auto-start */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="autoStart"
            checked={autoStart}
            onChange={(e) => setAutoStart(e.target.checked)}
            className="w-4 h-4 rounded border-secondary-700 bg-secondary-800 text-primary-600 focus:ring-primary-500"
          />
          <label htmlFor="autoStart" className="text-sm text-secondary-300">
            Start job immediately after creation
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-secondary-700">
          <button
            onClick={onClose}
            className="btn-secondary"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <span className="flex items-center space-x-2">
                <LoadingSpinner size="sm" />
                <span>Creating...</span>
              </span>
            ) : (
              `Create Job${autoStart ? ' & Start' : ''}`
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
