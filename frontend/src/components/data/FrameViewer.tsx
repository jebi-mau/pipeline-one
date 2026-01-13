/**
 * Pipeline One - Frame Viewer modal for displaying frame details
 */

import { useEffect, useState } from 'react';
import {
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useFrameDetail } from '../../hooks/useData';
import { AnnotatedImage } from './AnnotatedImage';
import { IMUDisplay } from './IMUDisplay';
import type { AnnotationSummary } from '../../types/data';

interface FrameViewerProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  frameId: string;
  onNavigate: (direction: 'prev' | 'next') => void;
}

export function FrameViewer({
  isOpen,
  onClose,
  jobId,
  frameId,
  onNavigate,
}: FrameViewerProps) {
  const { data: frame, isLoading, error } = useFrameDetail(jobId, frameId);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [showMasks, setShowMasks] = useState(true);

  // Reset selection when frame changes
  useEffect(() => {
    setSelectedAnnotationId(null);
  }, [frameId]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'ArrowLeft') {
        onNavigate('prev');
      } else if (e.key === 'ArrowRight') {
        onNavigate('next');
      } else if (e.key === 'Escape') {
        if (selectedAnnotationId) {
          setSelectedAnnotationId(null);
        } else {
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onNavigate, onClose, selectedAnnotationId]);

  // Handle annotation selection from list
  const handleListItemClick = (annId: string) => {
    setSelectedAnnotationId(prev => prev === annId ? null : annId);
  };

  if (!isOpen) return null;

  // Check if any annotations have masks
  const hasMasks = frame?.annotations.some(ann => ann.mask_url) ?? false;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="" size="full">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-secondary-700">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-medium text-secondary-100">
              Frame #{frame?.sequence_index.toString().padStart(4, '0') || '...'}
            </h2>
            {frame && (
              <span className="text-sm text-secondary-400">
                SVO2 Frame: {frame.svo2_frame_index}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {/* Mask toggle */}
            {hasMasks && (
              <button
                onClick={() => setShowMasks(!showMasks)}
                className={`p-2 rounded-lg ${
                  showMasks
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-700 text-secondary-300'
                } hover:bg-opacity-80`}
                title={showMasks ? 'Hide masks' : 'Show masks'}
              >
                {showMasks ? (
                  <EyeIcon className="w-5 h-5" />
                ) : (
                  <EyeSlashIcon className="w-5 h-5" />
                )}
              </button>
            )}
            <button
              onClick={() => onNavigate('prev')}
              className="p-2 rounded-lg bg-secondary-700 text-secondary-300 hover:bg-secondary-600"
              title="Previous (Left Arrow)"
            >
              <ChevronLeftIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => onNavigate('next')}
              className="p-2 rounded-lg bg-secondary-700 text-secondary-300 hover:bg-secondary-600"
              title="Next (Right Arrow)"
            >
              <ChevronRightIcon className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-secondary-700 text-secondary-300 hover:bg-secondary-600"
              title="Close (Escape)"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <LoadingSpinner size="lg" />
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-red-400">Failed to load frame details</p>
          </div>
        ) : frame ? (
          <div className="flex-1 overflow-auto p-4">
            {/* Images Row */}
            <div className="grid grid-cols-3 gap-4 mb-4">
              {/* Left Image */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-200">Left RGB</span>
                  {frame.image_left_url && (
                    <a
                      href={frame.image_left_url}
                      download
                      className="text-xs text-primary-400 hover:text-primary-300"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                    </a>
                  )}
                </div>
                {frame.image_left_url ? (
                  <AnnotatedImage
                    imageUrl={frame.image_left_url}
                    annotations={frame.annotations}
                    showMasks={showMasks}
                    selectedAnnotationId={selectedAnnotationId}
                    onSelectAnnotation={setSelectedAnnotationId}
                  />
                ) : (
                  <div className="aspect-video bg-secondary-700 rounded-lg flex items-center justify-center">
                    <span className="text-secondary-500">Not available</span>
                  </div>
                )}
              </div>

              {/* Right Image */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-200">Right RGB</span>
                  {frame.image_right_url && (
                    <a
                      href={frame.image_right_url}
                      download
                      className="text-xs text-primary-400 hover:text-primary-300"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                    </a>
                  )}
                </div>
                {frame.image_right_url ? (
                  <AnnotatedImage
                    imageUrl={frame.image_right_url}
                    annotations={frame.annotations}
                    showMasks={showMasks}
                    selectedAnnotationId={selectedAnnotationId}
                    onSelectAnnotation={setSelectedAnnotationId}
                  />
                ) : (
                  <div className="aspect-video bg-secondary-700 rounded-lg flex items-center justify-center">
                    <span className="text-secondary-500">Not available</span>
                  </div>
                )}
              </div>

              {/* Depth */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-200">Depth Map</span>
                  {frame.depth_url && (
                    <a
                      href={frame.depth_url}
                      download
                      className="text-xs text-primary-400 hover:text-primary-300"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4" />
                    </a>
                  )}
                </div>
                {frame.depth_url ? (
                  <div className="aspect-video bg-secondary-700 rounded-lg overflow-hidden">
                    <img
                      src={frame.depth_url}
                      alt="Depth"
                      className="w-full h-full object-contain"
                    />
                  </div>
                ) : (
                  <div className="aspect-video bg-secondary-700 rounded-lg flex items-center justify-center">
                    <span className="text-secondary-500">Not available</span>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Section - Annotations and Metadata */}
            <div className="grid grid-cols-2 gap-4">
              {/* Annotations List */}
              <div className="card p-4">
                <h3 className="text-sm font-medium text-secondary-200 mb-3">
                  Detections ({frame.annotations.length})
                  {selectedAnnotationId && (
                    <button
                      onClick={() => setSelectedAnnotationId(null)}
                      className="ml-2 text-xs text-secondary-400 hover:text-secondary-300"
                    >
                      Clear selection
                    </button>
                  )}
                </h3>
                {frame.annotations.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {frame.annotations.map((ann: AnnotationSummary) => {
                      const isSelected = selectedAnnotationId === ann.id;
                      return (
                        <div
                          key={ann.id}
                          onClick={() => handleListItemClick(ann.id)}
                          className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-primary-600/30 ring-1 ring-primary-500'
                              : 'bg-secondary-700/50 hover:bg-secondary-700'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <div
                              className={`w-3 h-3 rounded ${isSelected ? 'ring-2 ring-white' : ''}`}
                              style={{ backgroundColor: ann.class_color }}
                            />
                            <span className={`text-sm capitalize ${
                              isSelected ? 'text-white font-medium' : 'text-secondary-200'
                            }`}>
                              {ann.class_name}
                            </span>
                            {ann.mask_url && (
                              <span className="text-xs text-secondary-500" title="Has segmentation mask">
                                [mask]
                              </span>
                            )}
                          </div>
                          <div className="flex items-center space-x-3 text-xs text-secondary-400">
                            <span>{(ann.confidence * 100).toFixed(1)}%</span>
                            {ann.distance !== null && ann.distance !== undefined ? (
                              <span title="Center patch average depth">
                                {ann.distance.toFixed(2)}m
                              </span>
                            ) : ann.bbox_3d ? (
                              <span title="3D bounding box depth">
                                {ann.bbox_3d.z.toFixed(1)}m
                              </span>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-secondary-500">No detections</p>
                )}
              </div>

              {/* Frame Info */}
              <div className="card p-4">
                <h3 className="text-sm font-medium text-secondary-200 mb-3">Frame Info</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-secondary-400">Frame ID</span>
                    <span className="text-secondary-200 font-mono text-xs">
                      {frame.frame_id}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-secondary-400">SVO2 File</span>
                    <span className="text-secondary-200 truncate max-w-[200px]" title={frame.svo2_file}>
                      {frame.svo2_file}
                    </span>
                  </div>
                  {frame.timestamp_ns && (
                    <div className="flex justify-between">
                      <span className="text-secondary-400">Timestamp</span>
                      <span className="text-secondary-200">
                        {(frame.timestamp_ns / 1_000_000_000).toFixed(3)}s
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-secondary-400">Status</span>
                    <div className="flex space-x-1">
                      {frame.segmentation_complete && (
                        <span className="px-1.5 py-0.5 bg-green-600/20 text-green-400 rounded text-xs">
                          Seg
                        </span>
                      )}
                      {frame.reconstruction_complete && (
                        <span className="px-1.5 py-0.5 bg-blue-600/20 text-blue-400 rounded text-xs">
                          3D
                        </span>
                      )}
                      {frame.tracking_complete && (
                        <span className="px-1.5 py-0.5 bg-purple-600/20 text-purple-400 rounded text-xs">
                          Track
                        </span>
                      )}
                    </div>
                  </div>

                  {/* IMU Data */}
                  {frame.metadata && (
                    <div className="border-t border-secondary-700 mt-2 pt-2">
                      <IMUDisplay metadata={frame.metadata} />
                    </div>
                  )}

                  {/* Point Cloud Download */}
                  {frame.pointcloud_url && (
                    <div className="border-t border-secondary-700 mt-2 pt-2">
                      <a
                        href={frame.pointcloud_url}
                        download
                        className="flex items-center space-x-2 text-primary-400 hover:text-primary-300"
                      >
                        <ArrowDownTrayIcon className="w-4 h-4" />
                        <span>Download Point Cloud (PLY)</span>
                      </a>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
