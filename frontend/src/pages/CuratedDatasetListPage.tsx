/**
 * CuratedDatasetListPage - List all curated datasets
 * Step 3 output: Curated datasets ready for training export
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircleIcon,
  TrashIcon,
  DocumentArrowDownIcon,
  FunnelIcon,
  ChevronRightIcon,
  SparklesIcon,
  CubeIcon,
  CogIcon,
  EyeIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { curatedDatasetService } from '../services/curatedDatasetService';
import type { CuratedDataset } from '../types/curated_dataset';

export default function CuratedDatasetListPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['curated-datasets'],
    queryFn: () => curatedDatasetService.list({ limit: 100 }),
  });

  const deleteMutation = useMutation({
    mutationFn: curatedDatasetService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['curated-datasets'] });
    },
  });

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await deleteMutation.mutateAsync(id);
    } catch (err) {
      console.error('Failed to delete curated dataset:', err);
    }
  };

  const datasets = data?.curated_datasets ?? [];
  const filteredDatasets = searchQuery
    ? datasets.filter((d: CuratedDataset) =>
        d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : datasets;

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
        title="Failed to load curated datasets"
        message={error?.message || 'An error occurred while fetching curated datasets'}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Step Instructions */}
      <div className="bg-green-900/20 border border-green-700/50 rounded-xl p-4">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-600/30 border border-green-500 flex items-center justify-center">
            <span className="text-lg font-bold text-green-400">3</span>
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-secondary-100 mb-1">
              Curated Datasets
            </h2>
            <p className="text-sm text-secondary-400 mb-3">
              Curated datasets are filtered subsets of processed jobs. They capture your review
              decisions (excluded classes, diversity filtering, manual exclusions) as a named,
              versioned snapshot ready for training export.
            </p>
            <div className="flex items-center gap-6 text-xs text-secondary-500">
              <span className="flex items-center gap-1">
                <FunnelIcon className="w-3 h-3 text-green-400" />
                Filtered frames and annotations
              </span>
              <span className="flex items-center gap-1">
                <CheckCircleIcon className="w-3 h-3 text-green-400" />
                Reproducible configuration
              </span>
              <span className="flex items-center gap-1">
                <DocumentArrowDownIcon className="w-3 h-3 text-green-400" />
                Export to KITTI/COCO
              </span>
            </div>
          </div>
          <Link
            to="/review"
            className="btn-primary flex items-center gap-2 flex-shrink-0"
          >
            <SparklesIcon className="w-4 h-4" />
            Create New
          </Link>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-100">Curated Datasets</h1>
          <p className="text-sm text-secondary-400 mt-1">
            {datasets.length} curated dataset{datasets.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Search */}
        {datasets.length > 0 && (
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search datasets..."
              className="pl-9 pr-4 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}
      </div>

      {/* Datasets List */}
      {datasets.length === 0 ? (
        <EmptyState />
      ) : filteredDatasets.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-secondary-400">No curated datasets match your search.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDatasets.map((dataset: CuratedDataset) => (
            <CuratedDatasetCard
              key={dataset.id}
              dataset={dataset}
              onDelete={handleDelete}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Curated Dataset Card Component
function CuratedDatasetCard({
  dataset,
  onDelete,
  isDeleting,
}: {
  dataset: CuratedDataset;
  onDelete: (id: string, name: string) => void;
  isDeleting: boolean;
}) {
  const frameReduction = dataset.original_frame_count > 0
    ? Math.round(((dataset.original_frame_count - dataset.filtered_frame_count) / dataset.original_frame_count) * 100)
    : 0;

  const annotationReduction = dataset.original_annotation_count > 0
    ? Math.round(((dataset.original_annotation_count - dataset.filtered_annotation_count) / dataset.original_annotation_count) * 100)
    : 0;

  const hasFilters = dataset.filter_config && (
    dataset.filter_config.excluded_classes?.length > 0 ||
    dataset.filter_config.diversity_applied ||
    dataset.filter_config.excluded_frame_indices?.length > 0
  );

  return (
    <div className="card p-4 hover:border-secondary-600 transition-colors">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-12 h-12 rounded-lg bg-green-600/20 text-green-400 flex items-center justify-center flex-shrink-0">
          <CheckCircleIcon className="w-7 h-7" />
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <Link
              to={`/curated-datasets/${dataset.id}`}
              className="font-semibold text-secondary-100 hover:text-primary-300 transition-colors"
            >
              {dataset.name}
            </Link>
            <span className="text-xs px-2 py-0.5 bg-green-600/20 text-green-400 rounded-full">
              v{dataset.version}
            </span>
          </div>

          {dataset.description && (
            <p className="text-sm text-secondary-400 mb-2 line-clamp-1">
              {dataset.description}
            </p>
          )}

          {/* Lineage Path */}
          <div className="flex items-center gap-1.5 text-xs text-secondary-500 mb-3">
            <CubeIcon className="w-3 h-3 text-blue-400" />
            <span>{dataset.source_dataset_name || 'Dataset'}</span>
            <ChevronRightIcon className="w-3 h-3" />
            <CogIcon className="w-3 h-3 text-purple-400" />
            <span>{dataset.source_job_name || 'Job'}</span>
            <ChevronRightIcon className="w-3 h-3" />
            <CheckCircleIcon className="w-3 h-3 text-green-400" />
            <span className="text-green-400">Current</span>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-secondary-500">Frames:</span>
              <span className="text-secondary-300">{dataset.filtered_frame_count}</span>
              {frameReduction > 0 && (
                <span className="text-red-400">(-{frameReduction}%)</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-secondary-500">Annotations:</span>
              <span className="text-secondary-300">{dataset.filtered_annotation_count}</span>
              {annotationReduction > 0 && (
                <span className="text-red-400">(-{annotationReduction}%)</span>
              )}
            </div>
            {hasFilters && (
              <div className="flex items-center gap-1 text-yellow-400">
                <FunnelIcon className="w-3 h-3" />
                <span>Filters applied</span>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link
            to={`/curated-datasets/${dataset.id}`}
            className="btn-secondary text-sm py-1.5 px-3"
            title="View details"
          >
            <EyeIcon className="w-4 h-4" />
          </Link>
          <Link
            to={`/curated-datasets/${dataset.id}?export=true`}
            className="btn-primary text-sm py-1.5 px-3"
            title="Export training dataset"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
          </Link>
          <button
            onClick={() => onDelete(dataset.id, dataset.name)}
            className="p-1.5 rounded-lg transition-colors bg-red-600/20 text-red-400 hover:bg-red-600/40"
            title="Delete curated dataset"
            disabled={isDeleting}
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter Summary */}
      {hasFilters && dataset.filter_config && (
        <div className="mt-3 pt-3 border-t border-secondary-700">
          <div className="flex flex-wrap gap-2 text-xs">
            {dataset.filter_config.excluded_classes?.length > 0 && (
              <span className="px-2 py-1 bg-red-900/30 text-red-300 rounded">
                Excluded: {dataset.filter_config.excluded_classes.join(', ')}
              </span>
            )}
            {dataset.filter_config.diversity_applied && (
              <span className="px-2 py-1 bg-yellow-900/30 text-yellow-300 rounded">
                Diversity filter (threshold: {dataset.filter_config.diversity_similarity_threshold || 0.85})
              </span>
            )}
            {dataset.filter_config.excluded_frame_indices?.length > 0 && (
              <span className="px-2 py-1 bg-blue-900/30 text-blue-300 rounded">
                {dataset.filter_config.excluded_frame_indices.length} manual exclusions
              </span>
            )}
          </div>
        </div>
      )}

      {/* Created timestamp */}
      <div className="mt-3 text-xs text-secondary-500">
        Created {new Date(dataset.created_at).toLocaleDateString()} at{' '}
        {new Date(dataset.created_at).toLocaleTimeString()}
      </div>
    </div>
  );
}

// Empty State Component
function EmptyState() {
  return (
    <div className="card p-12 text-center">
      <div className="max-w-md mx-auto">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-600/20 flex items-center justify-center">
          <CheckCircleIcon className="w-10 h-10 text-green-400" />
        </div>
        <h2 className="text-xl font-bold text-secondary-100 mb-2">
          No Curated Datasets Yet
        </h2>
        <p className="text-secondary-400 mb-6">
          Curated datasets are created from the Review page after you&apos;ve filtered
          and refined your processed job results. They serve as the input for
          training dataset exports.
        </p>

        {/* Quick Guide */}
        <div className="bg-secondary-800/50 rounded-lg p-4 mb-6 text-left">
          <h3 className="text-sm font-semibold text-secondary-200 mb-3 flex items-center gap-2">
            <SparklesIcon className="w-5 h-5 text-green-400" />
            How to Create a Curated Dataset
          </h3>
          <ol className="text-sm text-secondary-400 space-y-2">
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600/30 text-green-400 text-xs flex items-center justify-center">
                1
              </span>
              Go to the Review page and select a completed job
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600/30 text-green-400 text-xs flex items-center justify-center">
                2
              </span>
              Apply filters: exclude classes, run diversity analysis
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600/30 text-green-400 text-xs flex items-center justify-center">
                3
              </span>
              Click &quot;Save as Curated Dataset&quot; to snapshot your filters
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-600/30 text-green-400 text-xs flex items-center justify-center">
                4
              </span>
              Export to KITTI or COCO format for training
            </li>
          </ol>
        </div>

        <Link to="/review" className="btn-primary">
          <SparklesIcon className="w-5 h-5 mr-2" />
          Go to Review
        </Link>
      </div>
    </div>
  );
}
