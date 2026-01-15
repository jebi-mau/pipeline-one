/**
 * Pipeline One - CurationSummaryPanel component
 * Shows review summary and "Save as Curated Dataset" action
 */

import { useState } from 'react';
import {
  CheckCircleIcon,
  FunnelIcon,
  SparklesIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { CreateCuratedDatasetModal } from './CreateCuratedDatasetModal';
import type { FilterConfig, ExclusionReasons } from '../../types/curated_dataset';

interface CurationSummaryPanelProps {
  jobId: string;
  jobName: string;
  // Original counts
  originalFrameCount: number;
  originalAnnotationCount: number;
  // Current filter state
  excludedClasses: string[];
  excludedAnnotationIds: string[];
  excludedFrameIndices: number[];
  // Diversity filter state
  diversityApplied: boolean;
  diversitySimilarityThreshold?: number;
  diversityMotionThreshold?: number;
  diversityExcludedFrames: number[];
  // Callbacks
  onCuratedDatasetCreated?: (id: string) => void;
}

export function CurationSummaryPanel({
  jobId,
  jobName,
  originalFrameCount,
  originalAnnotationCount,
  excludedClasses,
  excludedAnnotationIds,
  excludedFrameIndices,
  diversityApplied,
  diversitySimilarityThreshold,
  diversityMotionThreshold,
  diversityExcludedFrames,
  onCuratedDatasetCreated,
}: CurationSummaryPanelProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Calculate filtered counts
  const allExcludedFrames = new Set([...excludedFrameIndices, ...diversityExcludedFrames]);
  const filteredFrameCount = originalFrameCount - allExcludedFrames.size;
  const filteredAnnotationCount = originalAnnotationCount - excludedAnnotationIds.length;

  const framesRemoved = allExcludedFrames.size;
  const annotationsRemoved = excludedAnnotationIds.length;

  // Build filter config for saving
  const filterConfig: FilterConfig = {
    excluded_classes: excludedClasses,
    excluded_annotation_ids: excludedAnnotationIds.map(String),
    diversity_applied: diversityApplied,
    diversity_similarity_threshold: diversitySimilarityThreshold,
    diversity_motion_threshold: diversityMotionThreshold,
    excluded_frame_indices: Array.from(allExcludedFrames),
  };

  // Build exclusion reasons
  const exclusionReasons: ExclusionReasons = {
    class_filter: excludedAnnotationIds.filter((_, i) => i < excludedClasses.length * 10).map(String), // Simplified
    diversity: diversityExcludedFrames.map(String),
    manual: excludedFrameIndices.map(String),
  };

  const hasFilters = excludedClasses.length > 0 || diversityApplied || excludedFrameIndices.length > 0;

  return (
    <>
      <div className="bg-secondary-800/50 border border-secondary-700 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-secondary-200 flex items-center gap-2">
            <ChartBarIcon className="w-5 h-5 text-primary-400" />
            Curation Summary
          </h3>
          <span className="text-xs text-secondary-500">
            Source Job: {jobName}
          </span>
        </div>

        {/* Statistics comparison */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="p-3 bg-secondary-900/50 rounded-lg">
            <div className="text-xs text-secondary-500 mb-1">Frames</div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-secondary-300">
                {originalFrameCount}
              </span>
              {framesRemoved > 0 && (
                <>
                  <span className="text-secondary-500">→</span>
                  <span className="text-lg font-bold text-primary-400">
                    {filteredFrameCount}
                  </span>
                  <span className="text-xs text-red-400">
                    (-{framesRemoved})
                  </span>
                </>
              )}
            </div>
          </div>

          <div className="p-3 bg-secondary-900/50 rounded-lg">
            <div className="text-xs text-secondary-500 mb-1">Annotations</div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-secondary-300">
                {originalAnnotationCount}
              </span>
              {annotationsRemoved > 0 && (
                <>
                  <span className="text-secondary-500">→</span>
                  <span className="text-lg font-bold text-primary-400">
                    {filteredAnnotationCount}
                  </span>
                  <span className="text-xs text-red-400">
                    (-{annotationsRemoved})
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Active filters */}
        {hasFilters && (
          <div className="mb-4 p-3 bg-secondary-900/50 rounded-lg">
            <div className="text-xs text-secondary-500 mb-2 flex items-center gap-1">
              <FunnelIcon className="w-3 h-3" />
              Filters Applied
            </div>
            <div className="space-y-1 text-xs">
              {excludedClasses.length > 0 && (
                <div className="flex items-center gap-2 text-secondary-400">
                  <span className="w-2 h-2 bg-red-500 rounded-full" />
                  <span>Excluded classes: {excludedClasses.join(', ')}</span>
                </div>
              )}
              {diversityApplied && diversityExcludedFrames.length > 0 && (
                <div className="flex items-center gap-2 text-secondary-400">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full" />
                  <span>
                    Diversity filter: {diversityExcludedFrames.length} similar frames removed
                    {diversitySimilarityThreshold && (
                      <span className="text-secondary-500">
                        {' '}(threshold: {diversitySimilarityThreshold})
                      </span>
                    )}
                  </span>
                </div>
              )}
              {excludedFrameIndices.length > 0 && (
                <div className="flex items-center gap-2 text-secondary-400">
                  <span className="w-2 h-2 bg-blue-500 rounded-full" />
                  <span>Manual exclusions: {excludedFrameIndices.length} frames</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Save action */}
        <div className="flex items-center justify-between pt-3 border-t border-secondary-700">
          <div className="text-xs text-secondary-500">
            {hasFilters ? (
              <span className="flex items-center gap-1 text-green-400">
                <CheckCircleIcon className="w-4 h-4" />
                Ready to save as curated dataset
              </span>
            ) : (
              <span>No filters applied - all data will be included</span>
            )}
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <SparklesIcon className="w-4 h-4" />
            Save as Curated Dataset
          </button>
        </div>
      </div>

      {/* Create Modal */}
      <CreateCuratedDatasetModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        jobId={jobId}
        jobName={jobName}
        filterConfig={filterConfig}
        exclusionReasons={exclusionReasons}
        originalFrameCount={originalFrameCount}
        originalAnnotationCount={originalAnnotationCount}
        filteredFrameCount={filteredFrameCount}
        filteredAnnotationCount={filteredAnnotationCount}
        excludedFrameIds={Array.from(allExcludedFrames).map(String)}
        excludedAnnotationIds={excludedAnnotationIds.map(String)}
        onSuccess={(id) => {
          setShowCreateModal(false);
          onCuratedDatasetCreated?.(id);
        }}
      />
    </>
  );
}
