/**
 * CuratedDatasetDetailPage - Detailed view of a curated dataset with full lineage
 * Shows filter configuration, statistics, and export options
 */

import { useState } from 'react';
import { useParams, Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  FunnelIcon,
  DocumentArrowDownIcon,
  FolderIcon,
  ArrowPathIcon,
  ChartBarIcon,
  ClipboardDocumentIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { LineageTracePanel, type LineageStage } from '../components/common/LineageTracePanel';
import { curatedDatasetService } from '../services/curatedDatasetService';

export default function CuratedDatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const showExport = searchParams.get('export') === 'true';

  const { data: dataset, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['curated-dataset', id],
    queryFn: () => curatedDatasetService.get(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string }) =>
      curatedDatasetService.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['curated-dataset', id] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => curatedDatasetService.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['curated-datasets'] });
      navigate('/curated-datasets');
    },
  });

  const handleStartEdit = () => {
    if (dataset) {
      setEditName(dataset.name);
      setEditDescription(dataset.description || '');
      setIsEditing(true);
    }
  };

  const handleSaveEdit = async () => {
    await updateMutation.mutateAsync({
      name: editName,
      description: editDescription,
    });
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${dataset?.name}"? This cannot be undone.`)) return;
    await deleteMutation.mutateAsync();
  };

  const copyLineageToClipboard = () => {
    if (!dataset) return;
    const lineageJson = JSON.stringify({
      curated_dataset: {
        id: dataset.id,
        name: dataset.name,
        version: dataset.version,
        created_at: dataset.created_at,
      },
      source_job: {
        id: dataset.source_job_id,
        name: dataset.source_job_name,
      },
      source_dataset: {
        id: dataset.source_dataset_id,
        name: dataset.source_dataset_name,
      },
      filter_config: dataset.filter_config,
      statistics: {
        original_frame_count: dataset.original_frame_count,
        filtered_frame_count: dataset.filtered_frame_count,
        original_annotation_count: dataset.original_annotation_count,
        filtered_annotation_count: dataset.filtered_annotation_count,
      },
    }, null, 2);
    navigator.clipboard.writeText(lineageJson);
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
        title="Failed to load curated dataset"
        message={error?.message || 'The curated dataset could not be found'}
        onRetry={() => refetch()}
      />
    );
  }

  // Build lineage stages
  const lineageStages: LineageStage[] = [
    {
      type: 'raw',
      name: dataset.source_raw_data_path?.split('/').slice(-2).join('/') || 'Data Lake',
      subtitle: 'Raw SVO2 files',
    },
    {
      type: 'dataset',
      id: dataset.source_dataset_id ?? undefined,
      name: dataset.source_dataset_name || 'Source Dataset',
      link: dataset.source_dataset_id ? `/datasets/${dataset.source_dataset_id}` : undefined,
    },
    {
      type: 'job',
      id: dataset.source_job_id,
      name: dataset.source_job_name || 'Processing Job',
      link: `/jobs/${dataset.source_job_id}`,
    },
    {
      type: 'curated',
      id: dataset.id,
      name: dataset.name,
      subtitle: `v${dataset.version}`,
      isCurrent: true,
    },
  ];

  const frameReduction = dataset.original_frame_count > 0
    ? ((dataset.original_frame_count - dataset.filtered_frame_count) / dataset.original_frame_count * 100).toFixed(1)
    : '0';

  const annotationReduction = dataset.original_annotation_count > 0
    ? ((dataset.original_annotation_count - dataset.filtered_annotation_count) / dataset.original_annotation_count * 100).toFixed(1)
    : '0';

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Link
        to="/curated-datasets"
        className="inline-flex items-center gap-2 text-sm text-secondary-400 hover:text-secondary-200"
      >
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Curated Datasets
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-xl bg-green-600/20 text-green-400 flex items-center justify-center flex-shrink-0">
            <CheckCircleIcon className="w-8 h-8" />
          </div>
          <div>
            {isEditing ? (
              <div className="space-y-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="text-2xl font-bold bg-secondary-800 border border-secondary-600 rounded px-2 py-1 text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Description (optional)"
                  className="w-full text-sm bg-secondary-800 border border-secondary-600 rounded px-2 py-1 text-secondary-300 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveEdit}
                    className="btn-primary text-sm py-1 px-3"
                    disabled={updateMutation.isPending}
                  >
                    <CheckIcon className="w-4 h-4 mr-1" />
                    Save
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="btn-secondary text-sm py-1 px-3"
                  >
                    <XMarkIcon className="w-4 h-4 mr-1" />
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-secondary-100">{dataset.name}</h1>
                  <span className="text-sm px-2 py-0.5 bg-green-600/20 text-green-400 rounded-full">
                    v{dataset.version}
                  </span>
                  <button
                    onClick={handleStartEdit}
                    className="p-1 text-secondary-500 hover:text-secondary-300"
                    title="Edit name and description"
                  >
                    <PencilIcon className="w-4 h-4" />
                  </button>
                </div>
                {dataset.description && (
                  <p className="text-secondary-400 mt-1">{dataset.description}</p>
                )}
                <p className="text-sm text-secondary-500 mt-2">
                  Created {new Date(dataset.created_at).toLocaleDateString()} at{' '}
                  {new Date(dataset.created_at).toLocaleTimeString()}
                </p>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={copyLineageToClipboard}
            className="btn-secondary"
            title="Copy lineage JSON to clipboard"
          >
            <ClipboardDocumentIcon className="w-5 h-5 mr-2" />
            Copy Lineage
          </button>
          <button
            onClick={() => navigate(`/review/${dataset.source_job_id}`)}
            className="btn-secondary"
          >
            <ArrowPathIcon className="w-5 h-5 mr-2" />
            View in Review
          </button>
          <Link
            to={`/curated-datasets/${dataset.id}/export`}
            className="btn-primary"
          >
            <DocumentArrowDownIcon className="w-5 h-5 mr-2" />
            Export Training Dataset
          </Link>
          <button
            onClick={handleDelete}
            className="p-2 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40"
            title="Delete curated dataset"
            disabled={deleteMutation.isPending}
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Lineage Path */}
      <div className="card p-4">
        <h2 className="text-sm font-medium text-secondary-300 mb-3 flex items-center gap-2">
          <FolderIcon className="w-4 h-4 text-primary-400" />
          Data Lineage
        </h2>
        <LineageTracePanel stages={lineageStages} variant="horizontal" />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Statistics Panel */}
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-secondary-100 mb-4 flex items-center gap-2">
            <ChartBarIcon className="w-5 h-5 text-primary-400" />
            Curation Statistics
          </h2>

          <div className="space-y-4">
            {/* Frames */}
            <div className="bg-secondary-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-secondary-400">Frames</span>
                <span className="text-xs text-red-400">-{frameReduction}%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-secondary-300">
                  {dataset.original_frame_count.toLocaleString()}
                </span>
                <span className="text-secondary-500">→</span>
                <span className="text-2xl font-bold text-green-400">
                  {dataset.filtered_frame_count.toLocaleString()}
                </span>
              </div>
              <div className="mt-2 h-2 bg-secondary-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${(dataset.filtered_frame_count / dataset.original_frame_count) * 100}%` }}
                />
              </div>
            </div>

            {/* Annotations */}
            <div className="bg-secondary-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-secondary-400">Annotations</span>
                <span className="text-xs text-red-400">-{annotationReduction}%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-secondary-300">
                  {dataset.original_annotation_count.toLocaleString()}
                </span>
                <span className="text-secondary-500">→</span>
                <span className="text-2xl font-bold text-green-400">
                  {dataset.filtered_annotation_count.toLocaleString()}
                </span>
              </div>
              <div className="mt-2 h-2 bg-secondary-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${(dataset.filtered_annotation_count / dataset.original_annotation_count) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Filter Configuration Panel */}
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-secondary-100 mb-4 flex items-center gap-2">
            <FunnelIcon className="w-5 h-5 text-yellow-400" />
            Filter Configuration
          </h2>

          {dataset.filter_config ? (
            <div className="space-y-4">
              {/* Excluded Classes */}
              {dataset.filter_config.excluded_classes?.length > 0 && (
                <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-3">
                  <div className="text-sm font-medium text-red-300 mb-2">
                    Excluded Classes ({dataset.filter_config.excluded_classes.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {dataset.filter_config.excluded_classes.map((cls) => (
                      <span
                        key={cls}
                        className="px-2 py-1 bg-red-900/40 text-red-200 text-xs rounded"
                      >
                        {cls}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Diversity Filter */}
              {dataset.filter_config.diversity_applied && (
                <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-3">
                  <div className="text-sm font-medium text-yellow-300 mb-2">
                    Diversity Filter
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-secondary-500">Similarity Threshold:</span>
                      <span className="ml-2 text-secondary-200">
                        {dataset.filter_config.diversity_similarity_threshold || 0.85}
                      </span>
                    </div>
                    <div>
                      <span className="text-secondary-500">Motion Threshold:</span>
                      <span className="ml-2 text-secondary-200">
                        {dataset.filter_config.diversity_motion_threshold || 0.02}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Manual Exclusions */}
              {dataset.filter_config.excluded_frame_indices?.length > 0 && (
                <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-3">
                  <div className="text-sm font-medium text-blue-300 mb-1">
                    Manual Exclusions
                  </div>
                  <p className="text-sm text-secondary-400">
                    {dataset.filter_config.excluded_frame_indices.length} frames manually excluded
                  </p>
                </div>
              )}

              {/* No filters */}
              {!dataset.filter_config.excluded_classes?.length &&
                !dataset.filter_config.diversity_applied &&
                !dataset.filter_config.excluded_frame_indices?.length && (
                <div className="text-sm text-secondary-500 text-center py-4">
                  No filters applied - all data included
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-secondary-500 text-center py-4">
              No filter configuration available
            </div>
          )}
        </div>
      </div>

      {/* Exclusion Breakdown */}
      {dataset.exclusion_reasons && Object.keys(dataset.exclusion_reasons).length > 0 && (
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-secondary-100 mb-4">
            Exclusion Breakdown
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {dataset.exclusion_reasons.class_filter?.length > 0 && (
              <div className="bg-secondary-800/50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-red-400">
                  {dataset.exclusion_reasons.class_filter.length}
                </p>
                <p className="text-sm text-secondary-400 mt-1">
                  Removed by class filter
                </p>
              </div>
            )}
            {dataset.exclusion_reasons.diversity?.length > 0 && (
              <div className="bg-secondary-800/50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-yellow-400">
                  {dataset.exclusion_reasons.diversity.length}
                </p>
                <p className="text-sm text-secondary-400 mt-1">
                  Removed by diversity filter
                </p>
              </div>
            )}
            {dataset.exclusion_reasons.manual?.length > 0 && (
              <div className="bg-secondary-800/50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-blue-400">
                  {dataset.exclusion_reasons.manual.length}
                </p>
                <p className="text-sm text-secondary-400 mt-1">
                  Manually excluded
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Vertical Lineage View */}
      <div className="card p-5">
        <h2 className="text-lg font-semibold text-secondary-100 mb-4">
          Complete Data Lineage
        </h2>
        <LineageTracePanel stages={lineageStages} variant="vertical" />
      </div>

      {/* Export Modal Trigger */}
      {showExport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-secondary-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold text-secondary-100 mb-4">
              Export Training Dataset
            </h2>
            <p className="text-secondary-400 mb-4">
              Create a training dataset from this curated set.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => navigate(`/curated-datasets/${id}`)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <Link
                to={`/curated-datasets/${id}/export`}
                className="btn-primary"
              >
                Continue to Export
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
