/**
 * Pipeline One - CreateCuratedDatasetModal component
 * Modal for creating a new curated dataset from review filters
 */

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircleIcon,
  DocumentDuplicateIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { curatedDatasetService } from '../../services/curatedDatasetService';
import type {
  FilterConfig,
  ExclusionReasons,
  CreateCuratedDatasetRequest,
} from '../../types/curated_dataset';

interface CreateCuratedDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  jobName: string;
  filterConfig: FilterConfig;
  exclusionReasons: ExclusionReasons;
  originalFrameCount: number;
  originalAnnotationCount: number;
  filteredFrameCount: number;
  filteredAnnotationCount: number;
  excludedFrameIds: string[];
  excludedAnnotationIds: string[];
  onSuccess?: (id: string) => void;
}

export function CreateCuratedDatasetModal({
  isOpen,
  onClose,
  jobId,
  jobName,
  filterConfig,
  exclusionReasons,
  originalFrameCount,
  originalAnnotationCount,
  filteredFrameCount,
  filteredAnnotationCount,
  excludedFrameIds,
  excludedAnnotationIds,
  onSuccess,
}: CreateCuratedDatasetModalProps) {
  // Form state
  const [name, setName] = useState(() => {
    const date = new Date().toISOString().split('T')[0];
    return `${jobName.replace(/\s+/g, '_')}_curated_${date}`;
  });
  const [description, setDescription] = useState('');

  const queryClient = useQueryClient();

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const request: CreateCuratedDatasetRequest = {
        name,
        description: description || undefined,
        source_job_id: jobId,
        filter_config: filterConfig,
        original_frame_count: originalFrameCount,
        original_annotation_count: originalAnnotationCount,
        filtered_frame_count: filteredFrameCount,
        filtered_annotation_count: filteredAnnotationCount,
        excluded_frame_ids: excludedFrameIds,
        excluded_annotation_ids: excludedAnnotationIds,
        exclusion_reasons: exclusionReasons,
      };
      return curatedDatasetService.create(request);
    },
    onSuccess: (data) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['curated-datasets'] });
      queryClient.invalidateQueries({ queryKey: ['curated-datasets', jobId] });

      // Reset form
      setDescription('');

      // Callback
      onSuccess?.(data.id);
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await createMutation.mutateAsync();
  };

  const framesRemoved = originalFrameCount - filteredFrameCount;
  const annotationsRemoved = originalAnnotationCount - filteredAnnotationCount;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Save as Curated Dataset" size="md">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Summary */}
        <div className="p-4 bg-primary-900/20 border border-primary-600/30 rounded-lg">
          <h4 className="text-sm font-medium text-primary-300 mb-3 flex items-center gap-2">
            <DocumentDuplicateIcon className="w-4 h-4" />
            What will be saved
          </h4>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-secondary-500">Frames:</span>
              <span className="ml-2 font-medium text-secondary-200">
                {filteredFrameCount}
              </span>
              {framesRemoved > 0 && (
                <span className="ml-1 text-xs text-secondary-500">
                  (from {originalFrameCount})
                </span>
              )}
            </div>
            <div>
              <span className="text-secondary-500">Annotations:</span>
              <span className="ml-2 font-medium text-secondary-200">
                {filteredAnnotationCount}
              </span>
              {annotationsRemoved > 0 && (
                <span className="ml-1 text-xs text-secondary-500">
                  (from {originalAnnotationCount})
                </span>
              )}
            </div>
          </div>

          {/* Filter summary */}
          {(filterConfig.excluded_classes.length > 0 ||
            filterConfig.diversity_applied ||
            filterConfig.excluded_frame_indices.length > 0) && (
            <div className="mt-3 pt-3 border-t border-primary-600/30">
              <div className="flex items-center gap-1 text-xs text-secondary-400 mb-2">
                <FunnelIcon className="w-3 h-3" />
                <span>Filter configuration snapshot</span>
              </div>
              <ul className="text-xs text-secondary-500 space-y-1">
                {filterConfig.excluded_classes.length > 0 && (
                  <li>
                    Excluded classes: {filterConfig.excluded_classes.join(', ')}
                  </li>
                )}
                {filterConfig.diversity_applied && (
                  <li>
                    Diversity filter: {filterConfig.excluded_frame_indices.length} frames
                    {filterConfig.diversity_similarity_threshold && (
                      <span> (threshold: {filterConfig.diversity_similarity_threshold})</span>
                    )}
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>

        {/* Name input */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter curated dataset name..."
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            required
          />
          <p className="mt-1 text-xs text-secondary-500">
            A version number will be auto-assigned if you save multiple curations from the same job.
          </p>
        </div>

        {/* Description input */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add notes about this curation..."
            rows={3}
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
          />
        </div>

        {/* Error display */}
        {createMutation.isError && (
          <div className="p-3 bg-red-900/20 border border-red-600/30 rounded-lg text-sm text-red-400">
            Failed to create curated dataset. Please try again.
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-secondary-700">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary"
            disabled={createMutation.isPending}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || createMutation.isPending}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Creating...</span>
              </>
            ) : (
              <>
                <CheckCircleIcon className="w-4 h-4" />
                <span>Create Curated Dataset</span>
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
