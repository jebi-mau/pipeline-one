/**
 * Frame diversity panel for filtering similar/low-motion frames.
 */

import React, { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useReviewStore } from '../../stores/reviewStore';
import { reviewService } from '../../services/reviewService';

interface FrameDiversityPanelProps {
  jobId: string;
}

export const FrameDiversityPanel: React.FC<FrameDiversityPanelProps> = ({ jobId }) => {
  const {
    similarityThreshold,
    motionThreshold,
    diversityStatus,
    diversityResults,
    diversityApplied,
    totalFrames,
    setDiversityThresholds,
    setDiversityStatus,
    setDiversityResults,
    applyDiversity,
  } = useReviewStore();

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      setDiversityStatus('analyzing');
      return reviewService.analyzeDiversity(jobId, {
        similarity_threshold: similarityThreshold,
        motion_threshold: motionThreshold,
        sample_camera: 'left',
      });
    },
    onSuccess: (data) => {
      setDiversityResults(data);
    },
    onError: () => {
      setDiversityStatus('failed');
    },
  });

  const handleSimilarityChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setDiversityThresholds(parseFloat(e.target.value), motionThreshold);
    },
    [motionThreshold, setDiversityThresholds]
  );

  const handleMotionChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setDiversityThresholds(similarityThreshold, parseFloat(e.target.value));
    },
    [similarityThreshold, setDiversityThresholds]
  );

  const selectedCount = diversityResults?.selected_frame_count ?? totalFrames;
  const excludedCount = diversityResults?.excluded_frame_indices.length ?? 0;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Frame Diversity</h3>
        {diversityApplied && (
          <button
            onClick={() => applyDiversity(false)}
            className="text-sm text-yellow-400 hover:text-yellow-300"
          >
            Remove Filter
          </button>
        )}
      </div>

      {/* Threshold controls */}
      <div className="space-y-4 mb-4">
        {/* Similarity threshold */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-300">Similarity Threshold</span>
            <span className="text-white">{(similarityThreshold * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min={0.5}
            max={0.99}
            step={0.01}
            value={similarityThreshold}
            onChange={handleSimilarityChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:bg-blue-500
                       [&::-webkit-slider-thumb]:rounded-full"
          />
          <p className="text-xs text-gray-500 mt-1">
            Frames with similarity above this are considered duplicates
          </p>
        </div>

        {/* Motion threshold */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-300">Motion Threshold</span>
            <span className="text-white">{(motionThreshold * 100).toFixed(1)}%</span>
          </div>
          <input
            type="range"
            min={0.005}
            max={0.1}
            step={0.005}
            value={motionThreshold}
            onChange={handleMotionChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:bg-green-500
                       [&::-webkit-slider-thumb]:rounded-full"
          />
          <p className="text-xs text-gray-500 mt-1">
            Frames with motion below this are considered static
          </p>
        </div>
      </div>

      {/* Analyze button */}
      <button
        onClick={() => analyzeMutation.mutate()}
        disabled={diversityStatus === 'analyzing'}
        className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                   disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {diversityStatus === 'analyzing' ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Analyzing...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Analyze Diversity
          </>
        )}
      </button>

      {/* Results */}
      {diversityResults && diversityStatus === 'complete' && (
        <div className="mt-4 space-y-3">
          {/* Statistics */}
          <div className="p-3 bg-gray-700 rounded-lg">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-400">Selected frames:</span>
                <span className="ml-2 text-green-400 font-medium">
                  {selectedCount}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Excluded:</span>
                <span className="ml-2 text-red-400 font-medium">
                  {excludedCount}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Reduction:</span>
                <span className="ml-2 text-blue-400 font-medium">
                  {diversityResults.reduction_percent.toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400">Duplicates:</span>
                <span className="ml-2 text-yellow-400 font-medium">
                  {diversityResults.duplicate_pairs_found}
                </span>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Low-motion frames: {diversityResults.low_motion_frames}
            </div>
          </div>

          {/* Apply button */}
          {!diversityApplied ? (
            <button
              onClick={() => applyDiversity(true)}
              className="w-full py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg
                         flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Apply Diversity Filter
            </button>
          ) : (
            <div className="p-3 bg-green-600/20 border border-green-600 rounded-lg text-center">
              <span className="text-green-400 text-sm">Diversity filter applied</span>
            </div>
          )}
        </div>
      )}

      {diversityStatus === 'failed' && (
        <div className="mt-4 p-3 bg-red-600/20 border border-red-600 rounded-lg text-center">
          <span className="text-red-400 text-sm">Analysis failed. Please try again.</span>
        </div>
      )}

      {/* Info */}
      <div className="mt-4 text-xs text-gray-500">
        Uses perceptual hashing to detect similar frames and motion estimation to identify static sequences.
      </div>
    </div>
  );
};

export default FrameDiversityPanel;
