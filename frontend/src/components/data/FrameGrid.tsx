/**
 * Pipeline One - Frame Grid component for displaying frame thumbnails
 */

import { PhotoIcon, EyeIcon } from '@heroicons/react/24/outline';
import type { FrameSummary } from '../../types/data';

interface FrameGridProps {
  frames: FrameSummary[];
  jobId: string;
  onFrameClick: (frameId: string) => void;
}

export function FrameGrid({ frames, jobId: _jobId, onFrameClick }: FrameGridProps) {
  if (frames.length === 0) {
    return (
      <div className="card p-12 text-center">
        <p className="text-secondary-400">No frames found for this job.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-4 xl:grid-cols-6 gap-3">
      {frames.map((frame) => (
        <button
          key={frame.frame_id}
          onClick={() => onFrameClick(frame.frame_id)}
          className="card p-0 overflow-hidden group hover:ring-2 hover:ring-primary-500 transition-all"
        >
          {/* Thumbnail */}
          <div className="aspect-video bg-secondary-700 relative">
            {frame.thumbnail_url ? (
              <img
                src={frame.thumbnail_url}
                alt={`Frame ${frame.sequence_index}`}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <PhotoIcon className="w-8 h-8 text-secondary-500" />
              </div>
            )}

            {/* Frame number overlay */}
            <div className="absolute top-1 left-1 bg-black/60 px-1.5 py-0.5 rounded text-xs text-white">
              #{frame.sequence_index.toString().padStart(4, '0')}
            </div>

            {/* Detection count badge */}
            {frame.detection_count > 0 && (
              <div className="absolute top-1 right-1 bg-primary-600 px-1.5 py-0.5 rounded text-xs text-white flex items-center space-x-1">
                <EyeIcon className="w-3 h-3" />
                <span>{frame.detection_count}</span>
              </div>
            )}

            {/* Hover overlay */}
            <div className="absolute inset-0 bg-primary-600/20 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>

          {/* Frame Info */}
          <div className="p-2 text-left">
            <div className="text-xs text-secondary-300 truncate">
              SVO2: {frame.svo2_frame_index}
            </div>
            <div className="flex items-center space-x-1 mt-1">
              {frame.has_left_image && (
                <span className="w-2 h-2 rounded-full bg-green-500" title="Left Image" />
              )}
              {frame.has_right_image && (
                <span className="w-2 h-2 rounded-full bg-blue-500" title="Right Image" />
              )}
              {frame.has_depth && (
                <span className="w-2 h-2 rounded-full bg-purple-500" title="Depth" />
              )}
              {frame.has_pointcloud && (
                <span className="w-2 h-2 rounded-full bg-orange-500" title="Point Cloud" />
              )}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
