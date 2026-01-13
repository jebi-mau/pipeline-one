/**
 * DatasetsPage - Step 1 of the pipeline: Import and manage SVO2 datasets
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  FolderIcon,
  ArrowPathIcon,
  PlayIcon,
  TrashIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  InformationCircleIcon,
  FilmIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import {
  useDatasets,
  useCreateDataset,
  useDeleteDataset,
  useScanDataset,
  usePrepareDataset,
} from '../hooks/useDatasets';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import type { Dataset, DatasetCreate, JobSummary } from '../types/dataset';
import { datasetStatusColors, formatBytes } from '../types/dataset';

const jobStatusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  running: 'bg-blue-500',
  paused: 'bg-orange-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
};

// Dataset workflow states
const WORKFLOW_STEPS = {
  created: { step: 1, label: 'Created', action: 'Scan', next: 'Scan for SVO2 files' },
  scanning: { step: 2, label: 'Scanning', action: null, next: 'Finding files...' },
  scanned: { step: 2, label: 'Scanned', action: 'Prepare', next: 'Prepare files for processing' },
  preparing: { step: 3, label: 'Preparing', action: null, next: 'Preparing files...' },
  ready: { step: 4, label: 'Ready', action: 'Process', next: 'Ready for processing' },
  error: { step: 0, label: 'Error', action: 'Retry', next: 'Fix errors and retry' },
};

export default function DatasetsPage() {
  const navigate = useNavigate();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [expandedDatasets, setExpandedDatasets] = useState<Set<string>>(new Set());
  const { data: datasetsData, isLoading, isError, error, refetch } = useDatasets();

  const toggleExpanded = (datasetId: string) => {
    setExpandedDatasets((prev) => {
      const next = new Set(prev);
      if (next.has(datasetId)) {
        next.delete(datasetId);
      } else {
        next.add(datasetId);
      }
      return next;
    });
  };
  const createDataset = useCreateDataset();
  const deleteDataset = useDeleteDataset();
  const scanDataset = useScanDataset();
  const prepareDataset = usePrepareDataset();

  const datasets = datasetsData?.datasets ?? [];
  const readyDatasets = datasets.filter((d: Dataset) => d.status === 'ready');

  const handleCreateDataset = async (data: DatasetCreate) => {
    try {
      const result = await createDataset.mutateAsync(data);
      setIsCreateModalOpen(false);
      // Auto-navigate to the new dataset
      if (result?.id) {
        navigate(`/datasets/${result.id}`);
      }
    } catch (err) {
      console.error('Failed to create dataset:', err);
    }
  };

  const handleScan = async (datasetId: string) => {
    try {
      await scanDataset.mutateAsync({
        datasetId,
        request: { recursive: true, extract_metadata: true },
      });
    } catch (err) {
      console.error('Failed to scan dataset:', err);
    }
  };

  const handlePrepare = async (datasetId: string) => {
    try {
      await prepareDataset.mutateAsync({ datasetId });
    } catch (err) {
      console.error('Failed to prepare dataset:', err);
    }
  };

  const handleDelete = async (datasetId: string) => {
    if (!confirm('Are you sure you want to delete this dataset?')) return;
    try {
      await deleteDataset.mutateAsync(datasetId);
    } catch (err) {
      console.error('Failed to delete dataset:', err);
    }
  };

  const handleProcess = (datasetId: string) => {
    navigate('/jobs', { state: { datasetId, openCreateModal: true } });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage
        title="Failed to load datasets"
        message={error?.message || 'An error occurred while fetching datasets'}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Step Instructions */}
      <div className="bg-primary-900/20 border border-primary-700/50 rounded-xl p-4">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-600/30 border border-primary-500 flex items-center justify-center">
            <span className="text-lg font-bold text-primary-400">1</span>
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-secondary-100 mb-1">
              Import SVO2 Files
            </h2>
            <p className="text-sm text-secondary-400 mb-3">
              Create a dataset by pointing to a folder containing SVO2 files. The system will
              scan for files, extract metadata, and prepare them for processing.
            </p>
            <div className="flex items-center gap-6 text-xs text-secondary-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Scan: Find SVO2 files
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-yellow-500" />
                Prepare: Extract metadata
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                Ready: Process in Step 2
              </span>
            </div>
          </div>
          {readyDatasets.length > 0 && (
            <button
              onClick={() => navigate('/jobs', { state: { openCreateModal: true } })}
              className="btn-primary flex items-center gap-2 flex-shrink-0"
            >
              Continue to Processing
              <ArrowRightIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-100">Datasets</h1>
          <p className="text-sm text-secondary-400 mt-1">
            {datasets.length} dataset{datasets.length !== 1 ? 's' : ''}
            {readyDatasets.length > 0 && ` (${readyDatasets.length} ready for processing)`}
          </p>
        </div>
        <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary">
          <PlusIcon className="w-5 h-5 mr-2" />
          New Dataset
        </button>
      </div>

      {/* Datasets List */}
      {datasets.length === 0 ? (
        <EmptyState onCreateClick={() => setIsCreateModalOpen(true)} />
      ) : (
        <div className="space-y-3">
          {datasets.map((dataset: Dataset) => (
            <DatasetCard
              key={dataset.id}
              dataset={dataset}
              isExpanded={expandedDatasets.has(dataset.id)}
              onToggleExpand={() => toggleExpanded(dataset.id)}
              onScan={handleScan}
              onPrepare={handlePrepare}
              onProcess={handleProcess}
              onDelete={handleDelete}
              isScanning={scanDataset.isPending}
              isPreparing={prepareDataset.isPending}
              isDeleting={deleteDataset.isPending}
            />
          ))}
        </div>
      )}

      {/* Create Dataset Modal */}
      {isCreateModalOpen && (
        <CreateDatasetModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSubmit={handleCreateDataset}
          isLoading={createDataset.isPending}
        />
      )}
    </div>
  );
}

// Dataset Card Component - Collapsible with job stats
function DatasetCard({
  dataset,
  isExpanded,
  onToggleExpand,
  onScan,
  onPrepare,
  onProcess,
  onDelete,
  isScanning,
  isPreparing,
  isDeleting,
}: {
  dataset: Dataset;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onScan: (id: string) => void;
  onPrepare: (id: string) => void;
  onProcess: (id: string) => void;
  onDelete: (id: string) => void;
  isScanning: boolean;
  isPreparing: boolean;
  isDeleting: boolean;
}) {
  const workflow = WORKFLOW_STEPS[dataset.status as keyof typeof WORKFLOW_STEPS] || WORKFLOW_STEPS.created;
  const isReady = dataset.status === 'ready';
  const isProcessing = dataset.status === 'scanning' || dataset.status === 'preparing';
  const jobStats = dataset.job_stats || { total: 0, pending: 0, running: 0, completed: 0, failed: 0, jobs: [] };
  const hasJobs = jobStats.total > 0;

  return (
    <div
      className={`card transition-all ${
        isReady ? 'border-green-500/50 bg-green-900/10' : ''
      }`}
    >
      {/* Collapsed Header - Always visible */}
      <div
        className="p-4 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-4">
          {/* Expand/Collapse Icon */}
          <button className="text-secondary-400 hover:text-secondary-200">
            {isExpanded ? (
              <ChevronDownIcon className="w-5 h-5" />
            ) : (
              <ChevronRightIcon className="w-5 h-5" />
            )}
          </button>

          {/* Dataset Icon */}
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
              isReady
                ? 'bg-green-600/20 text-green-400'
                : 'bg-secondary-700 text-secondary-400'
            }`}
          >
            {isReady ? (
              <CheckCircleIcon className="w-6 h-6" />
            ) : (
              <FolderIcon className="w-6 h-6" />
            )}
          </div>

          {/* Dataset Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-secondary-100 truncate">
                {dataset.name}
              </h3>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                  datasetStatusColors[dataset.status] || 'bg-gray-500'
                } text-white flex-shrink-0`}
              >
                {workflow.label}
              </span>
            </div>
            <p className="text-xs text-secondary-500 mt-0.5">
              {dataset.customer && dataset.site
                ? `${dataset.customer} / ${dataset.site}`
                : dataset.customer || dataset.site || 'No location set'}
              {' • '}
              {dataset.total_files} file{dataset.total_files !== 1 ? 's' : ''} • {formatBytes(dataset.total_size_bytes)}
            </p>
          </div>

          {/* Job Stats Summary */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {hasJobs ? (
              <>
                {jobStats.running > 0 && (
                  <div className="flex items-center gap-1.5 text-blue-400">
                    <CpuChipIcon className="w-4 h-4 animate-pulse" />
                    <span className="text-sm font-medium">{jobStats.running}</span>
                  </div>
                )}
                {jobStats.completed > 0 && (
                  <div className="flex items-center gap-1.5 text-green-400">
                    <CheckCircleIcon className="w-4 h-4" />
                    <span className="text-sm font-medium">{jobStats.completed}</span>
                  </div>
                )}
                {jobStats.failed > 0 && (
                  <div className="flex items-center gap-1.5 text-red-400">
                    <ExclamationTriangleIcon className="w-4 h-4" />
                    <span className="text-sm font-medium">{jobStats.failed}</span>
                  </div>
                )}
                {jobStats.pending > 0 && (
                  <div className="flex items-center gap-1.5 text-yellow-400">
                    <ClockIcon className="w-4 h-4" />
                    <span className="text-sm font-medium">{jobStats.pending}</span>
                  </div>
                )}
              </>
            ) : (
              <span className="text-xs text-secondary-500">No jobs</span>
            )}
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            {dataset.status === 'created' && (
              <button
                onClick={() => onScan(dataset.id)}
                className="btn-secondary text-sm py-1.5 px-3"
                disabled={isScanning}
              >
                <ArrowPathIcon className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
              </button>
            )}
            {dataset.status === 'scanned' && (
              <button
                onClick={() => onPrepare(dataset.id)}
                className="btn-primary text-sm py-1.5 px-3"
                disabled={isPreparing}
              >
                <PlayIcon className={`w-4 h-4 ${isPreparing ? 'animate-pulse' : ''}`} />
              </button>
            )}
            {dataset.status === 'ready' && (
              <button
                onClick={() => onProcess(dataset.id)}
                className="btn-primary text-sm py-1.5 px-3"
              >
                <ArrowRightIcon className="w-4 h-4" />
              </button>
            )}
            {isProcessing && (
              <LoadingSpinner size="sm" />
            )}
            <Link
              to={`/datasets/${dataset.id}`}
              className="btn-secondary text-sm py-1.5 px-3"
            >
              <InformationCircleIcon className="w-4 h-4" />
            </Link>
            <button
              onClick={() => onDelete(dataset.id)}
              className="p-1.5 rounded-lg transition-colors bg-red-600/20 text-red-400 hover:bg-red-600/40"
              title="Delete dataset"
              disabled={isDeleting}
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-secondary-700 px-4 pb-4">
          {/* Progress Bar */}
          <div className="py-3">
            <div className="flex items-center justify-between text-xs text-secondary-500 mb-1">
              <span>{workflow.next}</span>
              <span>Step {workflow.step}/4</span>
            </div>
            <div className="h-1.5 bg-secondary-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  isReady ? 'bg-green-500' : 'bg-primary-500'
                }`}
                style={{ width: `${(workflow.step / 4) * 100}%` }}
              />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-secondary-800/50 rounded p-3 text-center">
              <p className="text-xl font-bold text-secondary-100">{dataset.total_files}</p>
              <p className="text-xs text-secondary-500">SVO2 Files</p>
            </div>
            <div className="bg-secondary-800/50 rounded p-3 text-center">
              <p className="text-xl font-bold text-secondary-100">{dataset.prepared_files}</p>
              <p className="text-xs text-secondary-500">Prepared</p>
            </div>
            <div className="bg-secondary-800/50 rounded p-3 text-center">
              <p className="text-xl font-bold text-secondary-100">{formatBytes(dataset.total_size_bytes)}</p>
              <p className="text-xs text-secondary-500">Total Size</p>
            </div>
            <div className="bg-secondary-800/50 rounded p-3 text-center">
              <p className="text-xl font-bold text-secondary-100">{jobStats.total}</p>
              <p className="text-xs text-secondary-500">Jobs</p>
            </div>
          </div>

          {/* Jobs List */}
          {hasJobs && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-secondary-300">Processing Jobs</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {jobStats.jobs.map((job: JobSummary) => (
                  <JobRow key={job.id} job={job} />
                ))}
              </div>
            </div>
          )}

          {/* No Jobs Message */}
          {!hasJobs && dataset.status === 'ready' && (
            <div className="text-center py-4 bg-secondary-800/30 rounded-lg">
              <p className="text-sm text-secondary-400 mb-2">No processing jobs yet</p>
              <button
                onClick={() => onProcess(dataset.id)}
                className="btn-primary text-sm"
              >
                <PlayIcon className="w-4 h-4 mr-2" />
                Start Processing
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Job Row Component for expanded dataset view
function JobRow({ job }: { job: JobSummary }) {
  const isRunning = job.status === 'running';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  return (
    <Link
      to={`/jobs/${job.id}`}
      className="flex items-center gap-3 p-2 bg-secondary-800/50 rounded-lg hover:bg-secondary-700/50 transition-colors"
    >
      {/* Status Icon */}
      <div className="flex-shrink-0">
        {isRunning ? (
          <CpuChipIcon className="w-5 h-5 text-blue-400 animate-pulse" />
        ) : isCompleted ? (
          <CheckCircleIcon className="w-5 h-5 text-green-400" />
        ) : isFailed ? (
          <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
        ) : (
          <ClockIcon className="w-5 h-5 text-secondary-400" />
        )}
      </div>

      {/* Job Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-secondary-100 truncate">
            {job.name}
          </span>
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
              jobStatusColors[job.status] || 'bg-gray-500'
            } text-white`}
          >
            {job.status}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-secondary-500 mt-0.5">
          {job.current_stage_name && isRunning && (
            <span>{job.current_stage_name}</span>
          )}
          {job.object_classes.length > 0 && (
            <span>{job.object_classes.slice(0, 3).join(', ')}{job.object_classes.length > 3 ? '...' : ''}</span>
          )}
          <span>{new Date(job.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Progress */}
      {isRunning && job.progress !== null && (
        <div className="flex-shrink-0 w-24">
          <div className="flex justify-between text-xs text-secondary-400 mb-1">
            <span>{job.progress.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-secondary-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Frames count for completed */}
      {isCompleted && job.total_frames && (
        <span className="text-xs text-secondary-400 flex-shrink-0">
          {job.total_frames.toLocaleString()} frames
        </span>
      )}

      {/* Error indicator */}
      {isFailed && job.error_message && (
        <span className="text-xs text-red-400 truncate max-w-32 flex-shrink-0" title={job.error_message}>
          Error
        </span>
      )}
    </Link>
  );
}

// Empty State Component
function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="card p-12 text-center">
      <div className="max-w-md mx-auto">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-primary-600/20 flex items-center justify-center">
          <FilmIcon className="w-10 h-10 text-primary-400" />
        </div>
        <h2 className="text-xl font-bold text-secondary-100 mb-2">
          No Datasets Yet
        </h2>
        <p className="text-secondary-400 mb-6">
          Create your first dataset to start the pipeline. Point to a folder containing
          SVO2 files from your ZED camera recordings.
        </p>

        {/* Quick Guide */}
        <div className="bg-secondary-800/50 rounded-lg p-4 mb-6 text-left">
          <h3 className="text-sm font-semibold text-secondary-200 mb-3 flex items-center gap-2">
            <InformationCircleIcon className="w-5 h-5 text-primary-400" />
            Quick Guide
          </h3>
          <ol className="text-sm text-secondary-400 space-y-2">
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary-600/30 text-primary-400 text-xs flex items-center justify-center">
                1
              </span>
              Click "New Dataset" and enter the path to your SVO2 files
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary-600/30 text-primary-400 text-xs flex items-center justify-center">
                2
              </span>
              Scan to discover all SVO2 files in the folder
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary-600/30 text-primary-400 text-xs flex items-center justify-center">
                3
              </span>
              Prepare files to extract metadata and make them ready
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary-600/30 text-primary-400 text-xs flex items-center justify-center">
                4
              </span>
              Continue to Step 2 to run extraction and detection
            </li>
          </ol>
        </div>

        <button onClick={onCreateClick} className="btn-primary">
          <PlusIcon className="w-5 h-5 mr-2" />
          Create Your First Dataset
        </button>
      </div>
    </div>
  );
}

// Create Dataset Modal
function CreateDatasetModal({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: DatasetCreate) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<DatasetCreate>({
    name: '',
    source_folder: '',
    description: '',
    customer: '',
    site: '',
    equipment: '',
    object_types: [],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />
        <div className="relative bg-secondary-800 rounded-xl shadow-xl max-w-lg w-full p-6">
          <h2 className="text-xl font-bold text-secondary-100 mb-2">
            Create New Dataset
          </h2>
          <p className="text-sm text-secondary-400 mb-4">
            Step 1 of the pipeline: Import SVO2 files for processing
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-300 mb-1">
                Dataset Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., Site A - January 2026"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-300 mb-1">
                Source Folder *
              </label>
              <input
                type="text"
                value={formData.source_folder}
                onChange={(e) =>
                  setFormData({ ...formData, source_folder: e.target.value })
                }
                className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="/path/to/svo2/files"
                required
              />
              <p className="text-xs text-secondary-500 mt-1">
                Path to the folder containing your SVO2 recordings
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-secondary-300 mb-1">
                  Customer
                </label>
                <input
                  type="text"
                  value={formData.customer || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, customer: e.target.value })
                  }
                  className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-300 mb-1">
                  Site
                </label>
                <input
                  type="text"
                  value={formData.site || ''}
                  onChange={(e) => setFormData({ ...formData, site: e.target.value })}
                  className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-300 mb-1">
                Equipment / Camera
              </label>
              <input
                type="text"
                value={formData.equipment || ''}
                onChange={(e) =>
                  setFormData({ ...formData, equipment: e.target.value })
                }
                className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., ZED 2i #001"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-300 mb-1">
                Description
              </label>
              <textarea
                value={formData.description || ''}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-3 py-2 bg-secondary-700 border border-secondary-600 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={2}
                placeholder="Optional notes about this dataset..."
              />
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-secondary-700">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Creating...
                  </>
                ) : (
                  'Create Dataset'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
