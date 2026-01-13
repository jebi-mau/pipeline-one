/**
 * Object filtering panel for including/excluding detected objects by class.
 */

import React from 'react';
import { useReviewStore } from '../../stores/reviewStore';
import type { AnnotationClassStats } from '../../types/review';

interface ObjectFilterPanelProps {
  classStats: AnnotationClassStats[];
  isLoading?: boolean;
}

export const ObjectFilterPanel: React.FC<ObjectFilterPanelProps> = ({
  classStats,
  isLoading = false,
}) => {
  const { excludedClasses, toggleClassFilter, resetFilters } = useReviewStore();

  const totalIncluded = classStats.reduce((sum, cls) => {
    return sum + (excludedClasses.has(cls.class_name) ? 0 : cls.total_count);
  }, 0);

  const totalAll = classStats.reduce((sum, cls) => sum + cls.total_count, 0);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Object Filtering</h3>
        <div className="animate-pulse space-y-3">
          <div className="h-10 bg-gray-700 rounded" />
          <div className="h-10 bg-gray-700 rounded" />
          <div className="h-10 bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Object Filtering</h3>
        {excludedClasses.size > 0 && (
          <button
            onClick={resetFilters}
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Reset
          </button>
        )}
      </div>

      {/* Summary */}
      <div className="mb-4 p-3 bg-gray-700 rounded-lg">
        <div className="flex justify-between text-sm">
          <span className="text-gray-300">Included annotations:</span>
          <span className="text-white font-medium">
            {totalIncluded} / {totalAll}
          </span>
        </div>
        {excludedClasses.size > 0 && (
          <div className="mt-1 text-xs text-yellow-400">
            {excludedClasses.size} class{excludedClasses.size > 1 ? 'es' : ''} excluded
          </div>
        )}
      </div>

      {/* Class list */}
      {classStats.length === 0 ? (
        <div className="text-center text-gray-400 py-4">No detections found</div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {classStats.map((cls) => {
            const isExcluded = excludedClasses.has(cls.class_name);
            return (
              <div
                key={cls.class_name}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  isExcluded
                    ? 'bg-gray-700/50 border-gray-600 opacity-60'
                    : 'bg-gray-700 border-transparent hover:border-gray-500'
                }`}
                onClick={() => toggleClassFilter(cls.class_name)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Color indicator */}
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: cls.class_color }}
                    />
                    {/* Class name */}
                    <span
                      className={`font-medium ${
                        isExcluded ? 'text-gray-400 line-through' : 'text-white'
                      }`}
                    >
                      {cls.class_name}
                    </span>
                  </div>
                  {/* Toggle indicator */}
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-400">
                      {cls.total_count} in {cls.frame_count} frames
                    </span>
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center ${
                        isExcluded
                          ? 'bg-red-600/30 text-red-400'
                          : 'bg-green-600/30 text-green-400'
                      }`}
                    >
                      {isExcluded ? (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </div>
                </div>
                {/* Confidence info */}
                <div className="mt-2 text-xs text-gray-500">
                  Avg confidence: {(cls.avg_confidence * 100).toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Instructions */}
      <div className="mt-4 text-xs text-gray-500">
        Click a class to include/exclude all instances from export.
      </div>
    </div>
  );
};

export default ObjectFilterPanel;
