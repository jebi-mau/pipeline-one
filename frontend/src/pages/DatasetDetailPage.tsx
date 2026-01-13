/**
 * Dataset Detail page with files, camera information, and lineage features
 */

import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  PlayIcon,
  FolderIcon,
  VideoCameraIcon,
  DocumentChartBarIcon,
  TagIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { useDataset, useDatasetCameras, useScanDataset, usePrepareDataset } from '../hooks/useDatasets';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { AnnotationMatchingView } from '../components/annotations/AnnotationMatchingView';
import { getDatasetSummary } from '../services/lineageService';
import { datasetStatusColors, formatBytes } from '../types/dataset';
import type { DatasetFileSummary, CameraInfo } from '../types/dataset';
import type { DatasetSummary } from '../types/lineage';

const fileStatusColors: Record<string, string> = {
  discovered: 'bg-gray-500',
  copying: 'bg-yellow-500',
  copied: 'bg-green-500',
  extracting: 'bg-blue-500',
  extracted: 'bg-green-600',
  failed: 'bg-red-500',
};

type TabType = 'overview' | 'files' | 'annotations' | 'lineage';

export default function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { data: dataset, isLoading, isError, error, refetch } = useDataset(datasetId);
  const { data: camerasData } = useDatasetCameras(datasetId);
  const scanDataset = useScanDataset();
  const prepareDataset = usePrepareDataset();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Fetch dataset summary for lineage tab
  useEffect(() => {
    if (!datasetId || activeTab !== 'lineage') return;

    async function fetchSummary() {
      setSummaryLoading(true);
      try {
        const data = await getDatasetSummary(datasetId!);
        setSummary(data);
      } catch (err) {
        console.error('Failed to load dataset summary:', err);
      } finally {
        setSummaryLoading(false);
      }
    }

    fetchSummary();
  }, [datasetId, activeTab]);

  const handleScan = async () => {
    if (!datasetId) return;
    try {
      await scanDataset.mutateAsync({
        datasetId,
        request: { recursive: true, extract_metadata: true },
      });
    } catch (err) {
      console.error('Failed to scan dataset:', err);
    }
  };

  const handlePrepare = async () => {
    if (!datasetId) return;
    try {
      await prepareDataset.mutateAsync({ datasetId });
    } catch (err) {
      console.error('Failed to prepare dataset:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError || !dataset) {
    return (
      <ErrorMessage
        title="Failed to load dataset"
        message={error?.message || 'Dataset not found'}
        onRetry={() => refetch()}
      />
    );
  }

  const isProcessing = dataset.status === 'scanning' || dataset.status === 'preparing';
  const cameras = camerasData?.cameras || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/datasets" className="text-secondary-400 hover:text-secondary-100">
            <ArrowLeftIcon className="w-5 h-5" />
          </Link>
          <h1 className="text-2xl font-bold text-secondary-100">{dataset.name}</h1>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              datasetStatusColors[dataset.status] || 'bg-gray-500'
            } text-white`}
          >
            {dataset.status}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {dataset.status === 'created' && (
            <button
              onClick={handleScan}
              className="btn-primary"
              disabled={scanDataset.isPending}
            >
              <ArrowPathIcon className="w-4 h-4 mr-2" />
              {scanDataset.isPending ? 'Scanning...' : 'Scan Folder'}
            </button>
          )}
          {dataset.status === 'scanned' && (
            <button
              onClick={handlePrepare}
              className="btn-primary"
              disabled={prepareDataset.isPending}
            >
              <PlayIcon className="w-4 h-4 mr-2" />
              {prepareDataset.isPending ? 'Preparing...' : 'Prepare Files'}
            </button>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-secondary-700">
        <nav className="flex space-x-8">
          {[
            { id: 'overview' as TabType, label: 'Overview', icon: DocumentChartBarIcon },
            { id: 'files' as TabType, label: 'Files', icon: FolderIcon },
            { id: 'annotations' as TabType, label: 'Annotations', icon: TagIcon },
            { id: 'lineage' as TabType, label: 'Lineage', icon: ClockIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 py-3 px-1 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-400'
                  : 'border-transparent text-secondary-400 hover:text-secondary-200 hover:border-secondary-500'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Progress (while processing) */}
      {isProcessing && (
        <div className="card p-6">
          <div className="flex items-center space-x-3">
            <LoadingSpinner size="sm" />
            <span className="text-secondary-100">
              {dataset.status === 'scanning' ? 'Scanning folder for SVO2 files...' : 'Preparing files...'}
            </span>
          </div>
          {dataset.status === 'preparing' && dataset.total_files > 0 && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-secondary-400 mb-1">
                <span>Progress</span>
                <span>{Math.round((dataset.prepared_files / dataset.total_files) * 100)}%</span>
              </div>
              <div className="w-full bg-secondary-600 rounded-full h-3">
                <div
                  className="bg-primary-500 h-3 rounded-full transition-all"
                  style={{ width: `${(dataset.prepared_files / dataset.total_files) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {dataset.status === 'failed' && dataset.error_message && (
        <div className="card p-6 border border-red-500/50">
          <h2 className="text-lg font-medium text-red-400 mb-2">Error</h2>
          <pre className="text-sm text-secondary-300 bg-secondary-900 p-4 rounded overflow-x-auto">
            {dataset.error_message}
          </pre>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <>
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-secondary-400 text-sm">Total Files</p>
          <p className="text-2xl font-bold text-secondary-100">{dataset.total_files}</p>
        </div>
        <div className="card p-4">
          <p className="text-secondary-400 text-sm">Total Size</p>
          <p className="text-2xl font-bold text-secondary-100">{formatBytes(dataset.total_size_bytes)}</p>
        </div>
        <div className="card p-4">
          <p className="text-secondary-400 text-sm">Prepared Files</p>
          <p className="text-2xl font-bold text-secondary-100">
            {dataset.prepared_files} / {dataset.total_files}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-secondary-400 text-sm">Jobs</p>
          <p className="text-2xl font-bold text-secondary-100">{dataset.job_count || 0}</p>
        </div>
      </div>

      {/* Dataset Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Metadata */}
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Metadata</h2>
          <dl className="space-y-3">
            {dataset.description && (
              <div>
                <dt className="text-secondary-400 text-sm">Description</dt>
                <dd className="text-secondary-100">{dataset.description}</dd>
              </div>
            )}
            {dataset.customer && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Customer</dt>
                <dd className="text-secondary-100">{dataset.customer}</dd>
              </div>
            )}
            {dataset.site && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Site</dt>
                <dd className="text-secondary-100">{dataset.site}</dd>
              </div>
            )}
            {dataset.equipment && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Equipment</dt>
                <dd className="text-secondary-100">{dataset.equipment}</dd>
              </div>
            )}
            {dataset.collection_date && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Collection Date</dt>
                <dd className="text-secondary-100">
                  {new Date(dataset.collection_date).toLocaleDateString()}
                </dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-secondary-400">Created</dt>
              <dd className="text-secondary-100">
                {new Date(dataset.created_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>

        {/* Paths */}
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Paths</h2>
          <dl className="space-y-4">
            <div>
              <dt className="text-secondary-400 text-sm flex items-center">
                <FolderIcon className="w-4 h-4 mr-1" />
                Source Folder
              </dt>
              <dd className="text-secondary-100 text-sm truncate font-mono mt-1">
                {dataset.source_folder}
              </dd>
            </div>
            {dataset.output_directory && (
              <div>
                <dt className="text-secondary-400 text-sm flex items-center">
                  <FolderIcon className="w-4 h-4 mr-1" />
                  Output Directory
                </dt>
                <dd className="text-secondary-100 text-sm truncate font-mono mt-1">
                  {dataset.output_directory}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      {/* Object Types */}
      {dataset.object_types && dataset.object_types.length > 0 && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Object Types</h2>
          <div className="flex flex-wrap gap-2">
            {dataset.object_types.map((type, index) => (
              <span
                key={index}
                className="px-3 py-1 bg-secondary-700 text-secondary-200 rounded-full text-sm"
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cameras */}
      {cameras.length > 0 && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4 flex items-center">
            <VideoCameraIcon className="w-5 h-5 mr-2" />
            Cameras ({cameras.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cameras.map((camera: CameraInfo) => (
              <div key={camera.camera_id} className="bg-secondary-700 rounded-lg p-4">
                <p className="font-medium text-secondary-100">{camera.camera_id}</p>
                {camera.camera_model && (
                  <p className="text-sm text-secondary-400">{camera.camera_model}</p>
                )}
                <div className="mt-2 flex justify-between text-sm">
                  <span className="text-secondary-400">{camera.file_count} files</span>
                  {camera.total_frames && (
                    <span className="text-secondary-400">{camera.total_frames.toLocaleString()} frames</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
        </>
      )}

      {/* Files Tab */}
      {activeTab === 'files' && (
        <>
      {/* Files Table */}
      {dataset.files && dataset.files.length > 0 && (
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-secondary-700">
            <h2 className="text-lg font-medium text-secondary-100">
              Files ({dataset.files.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Filename
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Camera
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Resolution
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Frames
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-700">
                {dataset.files.map((file: DatasetFileSummary) => (
                  <tr key={file.id} className="hover:bg-secondary-700/50">
                    <td className="px-4 py-3 text-sm text-secondary-100">
                      <div className="truncate max-w-xs" title={file.original_filename}>
                        {file.original_filename}
                      </div>
                      <div className="text-xs text-secondary-500 truncate max-w-xs" title={file.relative_path}>
                        {file.relative_path}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary-300">
                      {file.camera_id || '-'}
                      {file.camera_model && (
                        <div className="text-xs text-secondary-500">{file.camera_model}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary-300">
                      {file.resolution || '-'}
                      {file.fps && <span className="text-secondary-500 ml-1">@{file.fps}fps</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary-300">
                      {file.frame_count?.toLocaleString() || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-secondary-300">
                      {formatBytes(file.file_size)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          fileStatusColors[file.status] || 'bg-gray-500'
                        } text-white`}
                      >
                        {file.status}
                      </span>
                      {file.error_message && (
                        <div className="text-xs text-red-400 mt-1 truncate max-w-xs" title={file.error_message}>
                          {file.error_message}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State for Files */}
      {(!dataset.files || dataset.files.length === 0) && (
        <div className="card p-12 text-center">
          <FolderIcon className="w-16 h-16 mx-auto text-secondary-500 mb-4" />
          <p className="text-secondary-400 mb-4">
            No files discovered yet. Scan the source folder to find SVO2 files.
          </p>
        </div>
      )}
        </>
      )}

      {/* Annotations Tab */}
      {activeTab === 'annotations' && datasetId && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4 flex items-center">
            <TagIcon className="w-5 h-5 mr-2" />
            Annotation Matching
          </h2>
          <AnnotationMatchingView datasetId={datasetId} />
        </div>
      )}

      {/* Lineage Tab */}
      {activeTab === 'lineage' && (
        <div className="space-y-6">
          {summaryLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : summary ? (
            <>
              {/* Lineage Summary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="card p-4">
                  <p className="text-secondary-400 text-sm">Total Files</p>
                  <p className="text-2xl font-bold text-secondary-100">{summary.files.total}</p>
                  <p className="text-xs text-secondary-500 mt-1">
                    {summary.files.cameras.length} camera{summary.files.cameras.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="card p-4">
                  <p className="text-secondary-400 text-sm">Total Frames</p>
                  <p className="text-2xl font-bold text-secondary-100">{summary.frames.total.toLocaleString()}</p>
                  <p className="text-xs text-secondary-500 mt-1">
                    {summary.frames.extracted.toLocaleString()} extracted
                  </p>
                </div>
                <div className="card p-4">
                  <p className="text-secondary-400 text-sm">Annotations</p>
                  <p className="text-2xl font-bold text-secondary-100">{summary.annotations.total_annotations}</p>
                  <p className="text-xs text-secondary-500 mt-1">
                    {summary.annotations.matched} matched
                  </p>
                </div>
                <div className="card p-4">
                  <p className="text-secondary-400 text-sm">Jobs</p>
                  <p className="text-2xl font-bold text-secondary-100">{summary.jobs.total}</p>
                  <p className="text-xs text-secondary-500 mt-1">
                    {Object.entries(summary.jobs.by_status)
                      .map(([s, c]) => `${c} ${s}`)
                      .join(', ') || 'None'}
                  </p>
                </div>
              </div>

              {/* File Status Breakdown */}
              <div className="card p-6">
                <h3 className="text-lg font-medium text-secondary-100 mb-4">File Status Breakdown</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(summary.files.by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center space-x-3">
                      <span
                        className={`w-3 h-3 rounded-full ${fileStatusColors[status] || 'bg-gray-500'}`}
                      />
                      <span className="text-secondary-300">{status}</span>
                      <span className="text-secondary-100 font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cameras Overview */}
              {summary.files.cameras.length > 0 && (
                <div className="card p-6">
                  <h3 className="text-lg font-medium text-secondary-100 mb-4">Cameras</h3>
                  <div className="flex flex-wrap gap-2">
                    {summary.files.cameras.map((serial) => (
                      <span
                        key={serial}
                        className="px-3 py-1 bg-secondary-700 text-secondary-200 rounded-full text-sm font-mono"
                      >
                        {serial}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Data Provenance Info */}
              <div className="card p-6">
                <h3 className="text-lg font-medium text-secondary-100 mb-4">Data Provenance</h3>
                <dl className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-secondary-400">Total Data Size</dt>
                    <dd className="text-secondary-100">{formatBytes(summary.files.total_size_bytes)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-secondary-400">Annotation Imports</dt>
                    <dd className="text-secondary-100">{summary.annotations.total_imports}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-secondary-400">Unmatched Annotations</dt>
                    <dd className={summary.annotations.unmatched > 0 ? 'text-orange-400' : 'text-secondary-100'}>
                      {summary.annotations.unmatched}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-secondary-400">Dataset Created</dt>
                    <dd className="text-secondary-100">
                      {summary.dataset.created_at
                        ? new Date(summary.dataset.created_at).toLocaleString()
                        : 'N/A'}
                    </dd>
                  </div>
                </dl>
              </div>
            </>
          ) : (
            <div className="card p-12 text-center">
              <ClockIcon className="w-16 h-16 mx-auto text-secondary-500 mb-4" />
              <p className="text-secondary-400">
                Failed to load lineage information.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty State (only for overview tab) */}
      {activeTab === 'overview' && dataset.status === 'created' && (
        <div className="card p-12 text-center">
          <FolderIcon className="w-16 h-16 mx-auto text-secondary-500 mb-4" />
          <p className="text-secondary-400 mb-4">
            Dataset created. Click "Scan Folder" to discover SVO2 files.
          </p>
        </div>
      )}
    </div>
  );
}
