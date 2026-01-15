/**
 * Pipeline One - JobWizard component
 * Step-by-step wizard for creating new jobs
 */

import { useState, useEffect, useCallback } from 'react';
import {
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FolderIcon,
  DocumentIcon,
  HomeIcon,
  ArrowPathIcon,
  ChevronDownIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { LabelWithHelp } from '../common/HelpIcon';
import { ModelSelector } from './ModelSelector';
import { PresetSelector, BUILT_IN_PRESETS, type JobPreset } from './PresetSelector';
import { JOB_TOOLTIPS } from '../../constants/tooltips';
import { useBrowseFiles } from '../../hooks/useFiles';
import { useObjectClasses, useModelInfo } from '../../hooks/useConfig';
import { useDataset, useDatasets } from '../../hooks/useDatasets';
import type { PipelineStage } from '../../types/job';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';

// Wizard steps
const STEPS = [
  { id: 1, name: 'Basics', description: 'Name and source files' },
  { id: 2, name: 'Detection', description: 'Object classes' },
  { id: 3, name: 'Processing', description: 'Model and settings' },
  { id: 4, name: 'Review', description: 'Confirm and start' },
] as const;

interface JobWizardProps {
  onSubmit: (config: JobWizardConfig) => Promise<void>;
  onCancel: () => void;
  preselectedDatasetId?: string | null;
  isSubmitting?: boolean;
}

export interface JobWizardConfig {
  name: string;
  input_paths: string[];
  config: {
    object_class_ids: string[];
    sam3_model_variant: string;
    sam3_confidence_threshold: number;
    sam3_iou_threshold: number;
    sam3_batch_size: number;
    frame_skip: number;
    enable_tracking: boolean;
    export_3d_data: boolean;
    stages_to_run: PipelineStage[];
    enable_diversity_filter: boolean;
    diversity_similarity_threshold: number;
    diversity_motion_threshold: number;
  };
  autoStart: boolean;
}

// Quick access locations
const QUICK_LOCATIONS = [
  { name: 'Home', path: '/home/atlas', icon: HomeIcon },
  { name: 'SVO2 Data', path: '/home/atlas/dev/pipe1/data/svo2', icon: FolderIcon },
];

export function JobWizard({
  onSubmit,
  onCancel,
  preselectedDatasetId,
  isSubmitting = false,
}: JobWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1: Basics
  const [jobName, setJobName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [useDatasetFiles, setUseDatasetFiles] = useState(false);
  const [currentPath, setCurrentPath] = useState('/home/atlas/dev/pipe1/data/svo2');

  // Step 2: Detection
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);

  // Step 3: Processing
  const [selectedPreset, setSelectedPreset] = useState<JobPreset | null>(BUILT_IN_PRESETS[1]);
  const [selectedModel, setSelectedModel] = useState('sam3_hiera_small');
  const [confidence, setConfidence] = useState(0.5);
  const [iouThreshold, setIouThreshold] = useState(0.7);
  const [batchSize, setBatchSize] = useState(4);
  const [frameSkip, setFrameSkip] = useState(1);
  const [enableTracking, setEnableTracking] = useState(true);
  const [export3DData, setExport3DData] = useState(true);
  const [enableDiversityFilter, setEnableDiversityFilter] = useState(true);
  const [diversitySimilarityThreshold, setDiversitySimilarityThreshold] = useState(0.85);
  const [diversityMotionThreshold, setDiversityMotionThreshold] = useState(0.02);
  const [selectedStages, setSelectedStages] = useState<PipelineStage[]>([...ALL_PIPELINE_STAGES]);

  // Step 4: Review
  const [autoStart, setAutoStart] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Data hooks
  const { data: filesData, isLoading: filesLoading, refetch } = useBrowseFiles(currentPath, false);
  const { data: classesData, isLoading: classesLoading } = useObjectClasses();
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo();
  const { data: datasetsResponse } = useDatasets();
  const datasets = datasetsResponse?.datasets || [];
  const { data: datasetData } = useDataset(selectedDatasetId || undefined);

  // Handle preselected dataset
  useEffect(() => {
    if (preselectedDatasetId) {
      setSelectedDatasetId(preselectedDatasetId);
      setUseDatasetFiles(true);
    }
  }, [preselectedDatasetId]);

  // Populate from dataset
  useEffect(() => {
    if (datasetData && useDatasetFiles) {
      setJobName((prev) => prev || `${datasetData.name} - Processing`);

      let eligibleFiles = datasetData.files?.filter(
        (f) => f.status === 'copied' || f.status === 'extracted'
      ) || [];

      if (eligibleFiles.length === 0) {
        eligibleFiles = datasetData.files?.filter((f) => f.status === 'discovered') || [];
      }

      const filePaths = eligibleFiles.map(
        (f) => `${datasetData.source_folder}/${f.relative_path}`
      );

      if (filePaths.length > 0) {
        setSelectedFiles(filePaths);
        setCurrentPath(datasetData.source_folder);
      }
    }
  }, [datasetData, useDatasetFiles]);

  // Apply preset configuration
  const applyPreset = useCallback((preset: JobPreset) => {
    setSelectedPreset(preset);
    setSelectedModel(preset.config.sam3_model_variant);
    setConfidence(preset.config.sam3_confidence_threshold);
    setIouThreshold(preset.config.sam3_iou_threshold);
    setBatchSize(preset.config.sam3_batch_size);
    setFrameSkip(preset.config.frame_skip);
    setEnableTracking(preset.config.enable_tracking);
    setExport3DData(preset.config.export_3d_data);
    setEnableDiversityFilter(preset.config.enable_diversity_filter);
    setDiversitySimilarityThreshold(preset.config.diversity_similarity_threshold);
    setDiversityMotionThreshold(preset.config.diversity_motion_threshold);
    setSelectedStages(preset.config.stages_to_run);
  }, []);

  // File handling
  const handleSelectFile = (filePath: string) => {
    setSelectedFiles(prev =>
      prev.includes(filePath)
        ? prev.filter(f => f !== filePath)
        : [...prev, filePath]
    );
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

  // Class handling
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
      setSelectedClasses(allSelected ? [] : allNames);
    }
  };

  // Navigation
  const canGoNext = () => {
    switch (currentStep) {
      case 1:
        return jobName.trim() && selectedFiles.length > 0;
      case 2:
        return selectedClasses.length > 0;
      case 3:
        return selectedModel && selectedStages.length > 0;
      case 4:
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < 4 && canGoNext()) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    const config: JobWizardConfig = {
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
        enable_diversity_filter: enableDiversityFilter,
        diversity_similarity_threshold: diversitySimilarityThreshold,
        diversity_motion_threshold: diversityMotionThreshold,
      },
      autoStart,
    };

    await onSubmit(config);
  };

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <Step1Basics
            jobName={jobName}
            setJobName={setJobName}
            selectedFiles={selectedFiles}
            currentPath={currentPath}
            setCurrentPath={setCurrentPath}
            filesData={filesData}
            filesLoading={filesLoading}
            refetch={refetch}
            onSelectFile={handleSelectFile}
            onSelectAllSvo2={handleSelectAllSvo2}
            useDatasetFiles={useDatasetFiles}
            setUseDatasetFiles={setUseDatasetFiles}
            datasets={datasets}
            selectedDatasetId={selectedDatasetId}
            setSelectedDatasetId={setSelectedDatasetId}
            datasetData={datasetData}
          />
        );
      case 2:
        return (
          <Step2Detection
            classesData={classesData}
            classesLoading={classesLoading}
            selectedClasses={selectedClasses}
            onSelectClass={handleSelectClass}
            onSelectAllClasses={handleSelectAllClasses}
          />
        );
      case 3:
        return (
          <Step3Processing
            modelInfo={modelInfo}
            modelLoading={modelLoading}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            selectedPreset={selectedPreset}
            onSelectPreset={applyPreset}
            frameSkip={frameSkip}
            setFrameSkip={setFrameSkip}
            enableDiversityFilter={enableDiversityFilter}
            setEnableDiversityFilter={setEnableDiversityFilter}
            diversitySimilarityThreshold={diversitySimilarityThreshold}
            setDiversitySimilarityThreshold={setDiversitySimilarityThreshold}
            diversityMotionThreshold={diversityMotionThreshold}
            setDiversityMotionThreshold={setDiversityMotionThreshold}
          />
        );
      case 4:
        return (
          <Step4Review
            jobName={jobName}
            selectedFiles={selectedFiles}
            selectedClasses={selectedClasses}
            selectedModel={selectedModel}
            selectedPreset={selectedPreset}
            frameSkip={frameSkip}
            enableDiversityFilter={enableDiversityFilter}
            autoStart={autoStart}
            setAutoStart={setAutoStart}
            showAdvanced={showAdvanced}
            setShowAdvanced={setShowAdvanced}
            confidence={confidence}
            setConfidence={setConfidence}
            iouThreshold={iouThreshold}
            setIouThreshold={setIouThreshold}
            batchSize={batchSize}
            setBatchSize={setBatchSize}
            enableTracking={enableTracking}
            setEnableTracking={setEnableTracking}
            export3DData={export3DData}
            setExport3DData={setExport3DData}
            selectedStages={selectedStages}
          />
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress indicator */}
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div
              className={`
                flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors
                ${currentStep > step.id
                  ? 'bg-primary-500 border-primary-500 text-white'
                  : currentStep === step.id
                    ? 'border-primary-500 text-primary-500'
                    : 'border-secondary-600 text-secondary-500'
                }
              `}
            >
              {currentStep > step.id ? (
                <CheckIcon className="w-4 h-4" />
              ) : (
                <span className="text-sm font-medium">{step.id}</span>
              )}
            </div>
            <div className="ml-2 hidden sm:block">
              <p className={`text-sm font-medium ${
                currentStep >= step.id ? 'text-secondary-200' : 'text-secondary-500'
              }`}>
                {step.name}
              </p>
              <p className="text-xs text-secondary-500">{step.description}</p>
            </div>
            {index < STEPS.length - 1 && (
              <div className={`w-12 sm:w-20 h-0.5 mx-2 ${
                currentStep > step.id ? 'bg-primary-500' : 'bg-secondary-700'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="min-h-[400px]">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4 border-t border-secondary-700">
        <button
          onClick={currentStep === 1 ? onCancel : handleBack}
          className="btn-secondary flex items-center gap-2"
          disabled={isSubmitting}
        >
          <ChevronLeftIcon className="w-4 h-4" />
          {currentStep === 1 ? 'Cancel' : 'Back'}
        </button>

        {currentStep < 4 ? (
          <button
            onClick={handleNext}
            disabled={!canGoNext()}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            Next
            <ChevronRightIcon className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="btn-primary flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Creating...</span>
              </>
            ) : (
              <>
                <PlayIcon className="w-4 h-4" />
                <span>{autoStart ? 'Create & Start' : 'Create Job'}</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Step Components
// ============================================================================

interface Step1Props {
  jobName: string;
  setJobName: (name: string) => void;
  selectedFiles: string[];
  currentPath: string;
  setCurrentPath: (path: string) => void;
  filesData: any;
  filesLoading: boolean;
  refetch: () => void;
  onSelectFile: (path: string) => void;
  onSelectAllSvo2: () => void;
  useDatasetFiles: boolean;
  setUseDatasetFiles: (use: boolean) => void;
  datasets: any;
  selectedDatasetId: string | null;
  setSelectedDatasetId: (id: string | null) => void;
  datasetData: any;
}

function Step1Basics({
  jobName,
  setJobName,
  selectedFiles,
  currentPath,
  setCurrentPath,
  filesData,
  filesLoading,
  refetch,
  onSelectFile,
  onSelectAllSvo2,
  useDatasetFiles,
  setUseDatasetFiles,
  datasets,
  selectedDatasetId,
  setSelectedDatasetId,
  datasetData,
}: Step1Props) {
  return (
    <div className="space-y-6">
      {/* Job Name */}
      <div>
        <LabelWithHelp
          label="Job Name"
          helpContent="A descriptive name for this processing job. Auto-generated from dataset name if left empty."
          required
        />
        <input
          type="text"
          value={jobName}
          onChange={(e) => setJobName(e.target.value)}
          placeholder="Enter job name..."
          className="mt-2 w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Source Selection */}
      <div>
        <LabelWithHelp
          label="Source Files"
          helpContent="Select SVO2 files to process. You can choose from a dataset or browse the filesystem."
          required
        />

        {/* Toggle: Dataset vs File Browser */}
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => setUseDatasetFiles(true)}
            className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
              useDatasetFiles
                ? 'bg-primary-900/30 border-primary-500 text-primary-100'
                : 'bg-secondary-800 border-secondary-700 text-secondary-300 hover:border-secondary-500'
            }`}
          >
            From Dataset
          </button>
          <button
            onClick={() => setUseDatasetFiles(false)}
            className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
              !useDatasetFiles
                ? 'bg-primary-900/30 border-primary-500 text-primary-100'
                : 'bg-secondary-800 border-secondary-700 text-secondary-300 hover:border-secondary-500'
            }`}
          >
            Browse Files
          </button>
        </div>

        {/* Dataset Selector */}
        {useDatasetFiles && (
          <div className="mt-4">
            <select
              value={selectedDatasetId || ''}
              onChange={(e) => setSelectedDatasetId(e.target.value || null)}
              className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a dataset...</option>
              {datasets?.map((ds: any) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.total_files || 0} files)
                </option>
              ))}
            </select>
            {datasetData && (
              <p className="mt-2 text-sm text-secondary-400">
                {datasetData.files?.length || 0} files available from {datasetData.name}
              </p>
            )}
          </div>
        )}

        {/* File Browser */}
        {!useDatasetFiles && (
          <div className="mt-4">
            {/* Quick locations */}
            <div className="flex items-center gap-2 mb-2">
              {QUICK_LOCATIONS.map((loc) => (
                <button
                  key={loc.path}
                  onClick={() => setCurrentPath(loc.path)}
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
              <button
                onClick={() => refetch()}
                className="ml-auto p-1 text-secondary-400 hover:text-secondary-200"
                title="Refresh"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>
            </div>

            {/* File list */}
            <div className="bg-secondary-800 border border-secondary-700 rounded-lg max-h-48 overflow-y-auto">
              {filesLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : (
                <div className="divide-y divide-secondary-700">
                  {/* Go up */}
                  {currentPath !== '/' && (
                    <button
                      onClick={() => {
                        const parent = currentPath.split('/').slice(0, -1).join('/') || '/';
                        setCurrentPath(parent);
                      }}
                      className="w-full px-3 py-2 flex items-center gap-2 hover:bg-secondary-700 text-left"
                    >
                      <FolderIcon className="w-4 h-4 text-yellow-500" />
                      <span className="text-secondary-300">..</span>
                    </button>
                  )}

                  {/* Directories */}
                  {filesData?.directories?.map((dir: any) => (
                    <button
                      key={dir.path}
                      onClick={() => setCurrentPath(dir.path)}
                      className="w-full px-3 py-2 flex items-center gap-2 hover:bg-secondary-700 text-left"
                    >
                      <FolderIcon className="w-4 h-4 text-yellow-500" />
                      <span className="text-secondary-300">{dir.name}</span>
                    </button>
                  ))}

                  {/* SVO2 Files */}
                  {filesData?.files?.filter((f: any) => f.name.toLowerCase().endsWith('.svo2')).map((file: any) => (
                    <button
                      key={file.path}
                      onClick={() => onSelectFile(file.path)}
                      className={`w-full px-3 py-2 flex items-center justify-between text-left ${
                        selectedFiles.includes(file.path)
                          ? 'bg-primary-900/30'
                          : 'hover:bg-secondary-700'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <DocumentIcon className="w-4 h-4 text-blue-500" />
                        <span className="text-secondary-300">{file.name}</span>
                        <span className="text-xs text-secondary-500">
                          ({(file.size_bytes / 1024 / 1024).toFixed(1)} MB)
                        </span>
                      </div>
                      {selectedFiles.includes(file.path) && (
                        <CheckIcon className="w-4 h-4 text-primary-500" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Select all button */}
            {filesData?.files?.some((f: any) => f.name.toLowerCase().endsWith('.svo2')) && (
              <button
                onClick={onSelectAllSvo2}
                className="mt-2 text-xs text-primary-400 hover:text-primary-300"
              >
                Select all SVO2 files
              </button>
            )}
          </div>
        )}

        {/* Selected files summary */}
        {selectedFiles.length > 0 && (
          <div className="mt-4 p-3 bg-secondary-800/50 rounded-lg">
            <p className="text-sm text-secondary-300">
              <span className="font-medium text-primary-400">{selectedFiles.length}</span> files selected
            </p>
            <div className="mt-2 flex flex-wrap gap-1 max-h-20 overflow-y-auto">
              {selectedFiles.map((file) => (
                <span
                  key={file}
                  className="inline-flex items-center px-2 py-0.5 bg-primary-900/50 text-primary-300 rounded text-xs"
                >
                  {file.split('/').pop()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface Step2Props {
  classesData: any;
  classesLoading: boolean;
  selectedClasses: string[];
  onSelectClass: (name: string) => void;
  onSelectAllClasses: () => void;
}

function Step2Detection({
  classesData,
  classesLoading,
  selectedClasses,
  onSelectClass,
  onSelectAllClasses,
}: Step2Props) {
  // Group classes by category
  const categories = {
    vehicles: ['car', 'truck', 'bus', 'motorcycle', 'bicycle'],
    people: ['person', 'pedestrian'],
    animals: ['dog', 'cat', 'horse', 'bird'],
    infrastructure: ['traffic light', 'traffic sign', 'fire hydrant', 'stop sign'],
  };

  const selectCategory = (categoryClasses: string[]) => {
    const available = categoryClasses.filter(c =>
      classesData?.some((cls: any) => cls.name.toLowerCase() === c.toLowerCase())
    );
    const allSelected = available.every(c =>
      selectedClasses.some(sc => sc.toLowerCase() === c.toLowerCase())
    );

    if (allSelected) {
      // Deselect category
      const lowerAvailable = available.map(c => c.toLowerCase());
      selectedClasses.filter(c => !lowerAvailable.includes(c.toLowerCase())).forEach(() => {});
    } else {
      // Select category
      available.forEach(c => {
        const match = classesData?.find((cls: any) => cls.name.toLowerCase() === c.toLowerCase());
        if (match && !selectedClasses.includes(match.name)) {
          onSelectClass(match.name);
        }
      });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4">
          <LabelWithHelp
            label="Object Classes to Detect"
            helpContent={JOB_TOOLTIPS.objectClasses.description}
            required
          />
          <button
            onClick={onSelectAllClasses}
            className="text-sm text-primary-400 hover:text-primary-300"
          >
            {selectedClasses.length === (classesData?.length || 0) ? 'Deselect all' : 'Select all'}
          </button>
        </div>

        {/* Quick category buttons */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="text-xs text-secondary-500 py-1">Quick select:</span>
          {Object.entries(categories).map(([name, classes]) => (
            <button
              key={name}
              onClick={() => selectCategory(classes)}
              className="px-3 py-1 text-xs rounded-full bg-secondary-700 text-secondary-300 hover:bg-secondary-600 capitalize"
            >
              {name}
            </button>
          ))}
        </div>

        {/* Class grid */}
        {classesLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="md" />
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
            {classesData?.map((cls: any) => (
              <button
                key={cls.name}
                onClick={() => onSelectClass(cls.name)}
                className={`
                  px-3 py-2 rounded-lg text-sm font-medium transition-all border-2
                  ${selectedClasses.includes(cls.name)
                    ? 'border-transparent text-white'
                    : 'bg-secondary-800 border-secondary-700 text-secondary-300 hover:border-secondary-500'
                  }
                `}
                style={selectedClasses.includes(cls.name) ? { backgroundColor: cls.color } : {}}
              >
                {cls.name}
              </button>
            ))}
          </div>
        )}

        {/* Selection summary */}
        <p className="mt-4 text-sm text-secondary-400">
          <span className="font-medium text-primary-400">{selectedClasses.length}</span> classes selected
        </p>
      </div>
    </div>
  );
}

interface Step3Props {
  modelInfo: any;
  modelLoading: boolean;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  selectedPreset: JobPreset | null;
  onSelectPreset: (preset: JobPreset) => void;
  frameSkip: number;
  setFrameSkip: (skip: number) => void;
  enableDiversityFilter: boolean;
  setEnableDiversityFilter: (enable: boolean) => void;
  diversitySimilarityThreshold: number;
  setDiversitySimilarityThreshold: (t: number) => void;
  diversityMotionThreshold: number;
  setDiversityMotionThreshold: (t: number) => void;
}

function Step3Processing({
  modelInfo,
  modelLoading,
  selectedModel,
  setSelectedModel,
  selectedPreset,
  onSelectPreset,
  frameSkip,
  setFrameSkip,
  enableDiversityFilter,
  setEnableDiversityFilter,
  diversitySimilarityThreshold,
  setDiversitySimilarityThreshold,
  diversityMotionThreshold,
  setDiversityMotionThreshold,
}: Step3Props) {
  return (
    <div className="space-y-6">
      {/* Presets */}
      <PresetSelector
        onSelect={onSelectPreset}
        selectedPresetId={selectedPreset?.id}
      />

      {/* Model Selection */}
      {!modelLoading && modelInfo && (
        <ModelSelector
          models={modelInfo.available_models}
          selectedModel={selectedModel}
          onSelect={setSelectedModel}
          gpuName={modelInfo.gpu_name}
          gpuVramGb={modelInfo.vram_available_gb}
          defaultModel={modelInfo.default_model}
        />
      )}

      {/* Frame Skip */}
      <div>
        <LabelWithHelp
          label="Frame Skip"
          helpContent={JOB_TOOLTIPS.frameSkip.description + ' ' + JOB_TOOLTIPS.frameSkip.recommendation}
        />
        <div className="mt-2 flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="5"
            value={frameSkip}
            onChange={(e) => setFrameSkip(parseInt(e.target.value))}
            className="flex-1"
          />
          <span className="w-20 text-sm text-secondary-300">
            {frameSkip === 0 ? 'Every frame' : `Every ${frameSkip + 1} frames`}
          </span>
        </div>
      </div>

      {/* Diversity Filter */}
      <div className="p-4 bg-secondary-800/50 rounded-lg border border-secondary-700">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={enableDiversityFilter}
            onChange={(e) => setEnableDiversityFilter(e.target.checked)}
            className="w-4 h-4 rounded border-secondary-700 bg-secondary-800 text-primary-600"
          />
          <div>
            <span className="text-sm font-medium text-secondary-300">Enable Diversity Filter</span>
            <p className="text-xs text-secondary-500">
              Remove similar and low-motion frames during extraction
            </p>
          </div>
        </label>

        {enableDiversityFilter && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-secondary-400 mb-1">Similarity Threshold</label>
              <input
                type="number"
                min="0.5"
                max="0.99"
                step="0.05"
                value={diversitySimilarityThreshold}
                onChange={(e) => setDiversitySimilarityThreshold(parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-secondary-400 mb-1">Motion Threshold</label>
              <input
                type="number"
                min="0.005"
                max="0.1"
                step="0.005"
                value={diversityMotionThreshold}
                onChange={(e) => setDiversityMotionThreshold(parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-sm"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface Step4Props {
  jobName: string;
  selectedFiles: string[];
  selectedClasses: string[];
  selectedModel: string;
  selectedPreset: JobPreset | null;
  frameSkip: number;
  enableDiversityFilter: boolean;
  autoStart: boolean;
  setAutoStart: (start: boolean) => void;
  showAdvanced: boolean;
  setShowAdvanced: (show: boolean) => void;
  confidence: number;
  setConfidence: (c: number) => void;
  iouThreshold: number;
  setIouThreshold: (t: number) => void;
  batchSize: number;
  setBatchSize: (b: number) => void;
  enableTracking: boolean;
  setEnableTracking: (e: boolean) => void;
  export3DData: boolean;
  setExport3DData: (e: boolean) => void;
  selectedStages: PipelineStage[];
}

function Step4Review({
  jobName,
  selectedFiles,
  selectedClasses,
  selectedModel,
  selectedPreset,
  frameSkip,
  enableDiversityFilter,
  autoStart,
  setAutoStart,
  showAdvanced,
  setShowAdvanced,
  confidence,
  setConfidence,
  iouThreshold,
  setIouThreshold,
  batchSize,
  setBatchSize,
  enableTracking,
  setEnableTracking,
  export3DData,
  setExport3DData,
  selectedStages,
}: Step4Props) {
  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-secondary-800/50 rounded-lg">
          <h4 className="text-sm font-medium text-secondary-300 mb-2">Job Details</h4>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-secondary-500">Name:</dt>
              <dd className="text-secondary-200">{jobName}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-secondary-500">Files:</dt>
              <dd className="text-secondary-200">{selectedFiles.length}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-secondary-500">Classes:</dt>
              <dd className="text-secondary-200">{selectedClasses.length}</dd>
            </div>
          </dl>
        </div>

        <div className="p-4 bg-secondary-800/50 rounded-lg">
          <h4 className="text-sm font-medium text-secondary-300 mb-2">Processing</h4>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-secondary-500">Preset:</dt>
              <dd className="text-secondary-200">{selectedPreset?.name || 'Custom'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-secondary-500">Model:</dt>
              <dd className="text-secondary-200">{selectedModel.replace('sam3_hiera_', '')}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-secondary-500">Frame Skip:</dt>
              <dd className="text-secondary-200">{frameSkip}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-secondary-500">Diversity:</dt>
              <dd className="text-secondary-200">{enableDiversityFilter ? 'On' : 'Off'}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Pipeline stages */}
      <div className="p-4 bg-secondary-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-secondary-300 mb-2">Pipeline Stages</h4>
        <div className="flex flex-wrap gap-2">
          {selectedStages.map((stage) => (
            <span
              key={stage}
              className="px-2 py-1 bg-primary-900/50 text-primary-300 rounded text-xs"
            >
              {STAGE_INFO[stage].name}
            </span>
          ))}
        </div>
      </div>

      {/* Advanced Settings */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-secondary-400 hover:text-secondary-200"
        >
          <ChevronDownIcon className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
          <span>Advanced Settings</span>
        </button>

        {showAdvanced && (
          <div className="mt-4 p-4 bg-secondary-800/50 rounded-lg space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-secondary-400 mb-1">Confidence</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidence}
                  onChange={(e) => setConfidence(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-secondary-400 mb-1">IOU Threshold</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={iouThreshold}
                  onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-secondary-400 mb-1">Batch Size</label>
                <input
                  type="number"
                  min="1"
                  max="16"
                  value={batchSize}
                  onChange={(e) => setBatchSize(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-sm"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableTracking}
                  onChange={(e) => setEnableTracking(e.target.checked)}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-secondary-300">Enable Tracking</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={export3DData}
                  onChange={(e) => setExport3DData(e.target.checked)}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-secondary-300">Export 3D Data</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Auto-start option */}
      <label className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={autoStart}
          onChange={(e) => setAutoStart(e.target.checked)}
          className="w-4 h-4 rounded border-secondary-700 bg-secondary-800 text-primary-600"
        />
        <span className="text-sm text-secondary-300">Start job immediately after creation</span>
      </label>
    </div>
  );
}
