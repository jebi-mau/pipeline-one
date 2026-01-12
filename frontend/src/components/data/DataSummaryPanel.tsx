/**
 * Shalom - Data Summary Panel component
 */

import {
  PhotoIcon,
  CubeIcon,
  EyeIcon,
  DocumentTextIcon,
  FolderIcon,
} from '@heroicons/react/24/outline';
import type { DataSummary } from '../../types/data';

interface DataSummaryPanelProps {
  summary: DataSummary;
}

export function DataSummaryPanel({ summary }: DataSummaryPanelProps) {
  const stats = [
    {
      label: 'Total Frames',
      value: summary.total_frames.toLocaleString(),
      icon: DocumentTextIcon,
    },
    {
      label: 'Left Images',
      value: summary.frames_with_left_image.toLocaleString(),
      icon: PhotoIcon,
    },
    {
      label: 'Right Images',
      value: summary.frames_with_right_image.toLocaleString(),
      icon: PhotoIcon,
    },
    {
      label: 'Depth Maps',
      value: summary.frames_with_depth.toLocaleString(),
      icon: CubeIcon,
    },
    {
      label: 'Point Clouds',
      value: summary.frames_with_pointcloud.toLocaleString(),
      icon: CubeIcon,
    },
  ];

  return (
    <div className="card p-4 space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-lg font-medium text-secondary-100">{summary.job_name}</h3>
        <p className="text-sm text-secondary-400">Frame Skip: {summary.frame_skip}</p>
      </div>

      {/* Stats Grid */}
      <div className="space-y-2">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="flex items-center justify-between py-2 border-b border-secondary-700 last:border-0"
          >
            <div className="flex items-center space-x-2">
              <stat.icon className="w-4 h-4 text-secondary-400" />
              <span className="text-sm text-secondary-300">{stat.label}</span>
            </div>
            <span className="text-sm font-medium text-secondary-100">{stat.value}</span>
          </div>
        ))}
      </div>

      {/* Detections */}
      <div className="pt-2 border-t border-secondary-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <EyeIcon className="w-4 h-4 text-secondary-400" />
            <span className="text-sm text-secondary-300">Detections</span>
          </div>
          <span className="text-sm font-medium text-secondary-100">
            {summary.total_detections.toLocaleString()}
          </span>
        </div>

        {Object.keys(summary.detections_by_class).length > 0 && (
          <div className="space-y-1 mt-2">
            {Object.entries(summary.detections_by_class)
              .sort(([, a], [, b]) => b - a)
              .map(([className, count]) => (
                <div
                  key={className}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-secondary-400 capitalize">{className}</span>
                  <span className="text-secondary-300">{count.toLocaleString()}</span>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Tracks */}
      {summary.total_tracks > 0 && (
        <div className="pt-2 border-t border-secondary-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-secondary-300">Tracks</span>
            <span className="text-sm font-medium text-secondary-100">
              {summary.total_tracks.toLocaleString()}
            </span>
          </div>
        </div>
      )}

      {/* SVO2 Sources */}
      <div className="pt-2 border-t border-secondary-700">
        <div className="flex items-center space-x-2 mb-2">
          <FolderIcon className="w-4 h-4 text-secondary-400" />
          <span className="text-sm text-secondary-300">SVO2 Sources</span>
        </div>
        <div className="space-y-2">
          {summary.svo2_files.map((file) => (
            <div
              key={file.path}
              className="text-xs bg-secondary-700/50 rounded p-2"
            >
              <div className="font-medium text-secondary-200 truncate" title={file.filename}>
                {file.filename}
              </div>
              <div className="text-secondary-400 mt-1">
                {file.frames_extracted} frames extracted
                {file.total_frames_original && (
                  <span> (of {file.total_frames_original})</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Output Directory */}
      {summary.output_directory && (
        <div className="pt-2 border-t border-secondary-700">
          <div className="text-xs text-secondary-500 truncate" title={summary.output_directory}>
            Output: {summary.output_directory}
          </div>
        </div>
      )}
    </div>
  );
}
