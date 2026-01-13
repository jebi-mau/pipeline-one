/**
 * Modal for creating and exporting training datasets.
 */

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useReviewStore } from '../../stores/reviewStore';
import { reviewService } from '../../services/reviewService';
import type { TrainingDatasetRequest } from '../../types/review';

interface TrainingDatasetModalProps {
  jobId: string;
  onClose: () => void;
}

export const TrainingDatasetModal: React.FC<TrainingDatasetModalProps> = ({
  jobId,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const { getFilterConfig, getSelectedFrameCount, totalFrames } = useReviewStore();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [format, setFormat] = useState<'kitti' | 'coco' | 'both'>('both');
  const [trainRatio, setTrainRatio] = useState(0.7);
  const [valRatio, setValRatio] = useState(0.2);
  const [testRatio, setTestRatio] = useState(0.1);
  const [includeMasks, setIncludeMasks] = useState(true);
  const [includeDepth, setIncludeDepth] = useState(true);
  const [include3DBoxes, setInclude3DBoxes] = useState(false);

  const createMutation = useMutation({
    mutationFn: async () => {
      const request: TrainingDatasetRequest = {
        name,
        description: description || undefined,
        format,
        filter_config: getFilterConfig(),
        train_ratio: trainRatio,
        val_ratio: valRatio,
        test_ratio: testRatio,
        shuffle_seed: 42,
        include_masks: includeMasks,
        include_depth: includeDepth,
        include_3d_boxes: include3DBoxes,
      };
      return reviewService.createTrainingDataset(jobId, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-datasets'] });
      onClose();
    },
  });

  const selectedFrameCount = getSelectedFrameCount();
  const ratioSum = trainRatio + valRatio + testRatio;
  const isRatioValid = Math.abs(ratioSum - 1.0) < 0.01;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Create Training Dataset</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Summary */}
          <div className="p-3 bg-gray-700 rounded-lg">
            <div className="text-sm text-gray-300">
              Selected frames: <span className="text-white font-medium">{selectedFrameCount}</span> / {totalFrames}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">Dataset Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., truck-detection-v1"
              className="w-full bg-gray-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={2}
              className="w-full bg-gray-700 text-white rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Format */}
          <div>
            <label className="block text-sm text-gray-300 mb-2">Export Format</label>
            <div className="flex gap-4">
              {(['kitti', 'coco', 'both'] as const).map((f) => (
                <label key={f} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="format"
                    value={f}
                    checked={format === f}
                    onChange={() => setFormat(f)}
                    className="text-blue-500"
                  />
                  <span className="text-white capitalize">{f}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Split ratios */}
          <div>
            <label className="block text-sm text-gray-300 mb-2">Train/Val/Test Split</label>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Train</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={trainRatio}
                  onChange={(e) => setTrainRatio(parseFloat(e.target.value) || 0)}
                  className="w-full bg-gray-700 text-white rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Validation</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={valRatio}
                  onChange={(e) => setValRatio(parseFloat(e.target.value) || 0)}
                  className="w-full bg-gray-700 text-white rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Test</label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={testRatio}
                  onChange={(e) => setTestRatio(parseFloat(e.target.value) || 0)}
                  className="w-full bg-gray-700 text-white rounded px-2 py-1 text-sm"
                />
              </div>
            </div>
            {!isRatioValid && (
              <p className="text-xs text-yellow-400 mt-1">
                Ratios should sum to 1.0 (current: {ratioSum.toFixed(2)})
              </p>
            )}
          </div>

          {/* Include options */}
          <div>
            <label className="block text-sm text-gray-300 mb-2">Include Data</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeMasks}
                  onChange={(e) => setIncludeMasks(e.target.checked)}
                  className="rounded text-blue-500"
                />
                <span className="text-white text-sm">Segmentation masks</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeDepth}
                  onChange={(e) => setIncludeDepth(e.target.checked)}
                  className="rounded text-blue-500"
                />
                <span className="text-white text-sm">Depth maps</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={include3DBoxes}
                  onChange={(e) => setInclude3DBoxes(e.target.checked)}
                  className="rounded text-blue-500"
                />
                <span className="text-white text-sm">3D bounding boxes</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={!name || !isRatioValid || createMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded
                       disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {createMutation.isPending ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Create Dataset
              </>
            )}
          </button>
        </div>

        {/* Error */}
        {createMutation.isError && (
          <div className="px-4 pb-4">
            <div className="p-3 bg-red-600/20 border border-red-600 rounded text-red-400 text-sm">
              Failed to create training dataset. Please try again.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrainingDatasetModal;
