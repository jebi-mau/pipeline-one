/**
 * Review Page - Step 3 in the Pipeline One workflow.
 *
 * Provides frame-by-frame and video playback review, object filtering,
 * frame diversity analysis, and training dataset export.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useReviewStore } from '../stores/reviewStore';
import { reviewService } from '../services/reviewService';
import { jobsService } from '../services/jobsService';
import { dataService } from '../services/dataService';
import { datasetService } from '../services/datasetService';
import {
  FrameDiversityPanel,
  ObjectFilterPanel,
  PlaybackControls,
  TrainingDatasetModal,
} from '../components/review';
import { AnnotatedImage } from '../components/data/AnnotatedImage';
import { IMUDisplay } from '../components/data/IMUDisplay';
import {
  CheckCircleIcon,
  ClockIcon,
  FilmIcon,
  CubeIcon,
  FolderIcon,
  ChevronRightIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import type { JobResponse } from '../types/job';
import type { Dataset } from '../types/dataset';

// Helper to format relative time
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// Helper to format duration
function formatDuration(startStr: string, endStr: string): string {
  const start = new Date(startStr);
  const end = new Date(endStr);
  const diffMs = end.getTime() - start.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const mins = Math.floor(diffSecs / 60);
  const secs = diffSecs % 60;
  if (mins > 0) return `${mins}m ${secs}s`;
  return `${secs}s`;
}

const ReviewPage: React.FC = () => {
  const {
    jobId,
    currentFrameIndex,
    totalFrames,
    isExportModalOpen,
    excludedClasses,
    setJobId,
    setFrames,
    openExportModal,
    closeExportModal,
    resetAll,
  } = useReviewStore();

  const [showJobSelector, setShowJobSelector] = useState(!jobId);
  const [cameraView, setCameraView] = useState<'left' | 'right'>('left');
  const { isPlaying } = useReviewStore();

  // Fetch completed jobs
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs', 'completed'],
    queryFn: () => jobsService.list({ status: 'completed', limit: 100 }),
  });

  // Fetch all datasets for mapping
  const { data: datasetsData } = useQuery({
    queryKey: ['datasets-for-review'],
    queryFn: () => datasetService.list({ limit: 100 }),
  });

  // Create dataset lookup map
  const datasetMap = useMemo(() => {
    const map = new Map<string, Dataset>();
    if (datasetsData?.datasets) {
      datasetsData.datasets.forEach((ds) => map.set(ds.id, ds));
    }
    return map;
  }, [datasetsData]);

  // Filter to completed jobs (removed output_directory requirement)
  const completedJobs = useMemo(() => {
    return (jobsData?.jobs ?? []).filter(
      (job: JobResponse) => job.status === 'completed'
    );
  }, [jobsData]);

  // Get current selected job details
  const selectedJob = useMemo(() => {
    return completedJobs.find((j) => j.id === jobId);
  }, [completedJobs, jobId]);

  // Fetch frames for selected job (API max limit is 500)
  const { data: framesData, isLoading: framesLoading } = useQuery({
    queryKey: ['frames', jobId],
    queryFn: () => dataService.listFrames(jobId!, { limit: 500 }),
    enabled: !!jobId,
  });

  // Fetch annotation stats for filtering
  const { data: annotationStats, isLoading: statsLoading } = useQuery({
    queryKey: ['annotation-stats', jobId],
    queryFn: () => reviewService.getAnnotationStats(jobId!),
    enabled: !!jobId,
  });

  // Fetch current frame detail
  const currentFrameId = framesData?.frames[currentFrameIndex]?.frame_id;
  const { data: frameDetail } = useQuery({
    queryKey: ['frame-detail', jobId, currentFrameId],
    queryFn: () => dataService.getFrameDetail(jobId!, currentFrameId!),
    enabled: !!jobId && !!currentFrameId,
    staleTime: 60000, // Keep data fresh for 60 seconds
    gcTime: 300000,   // Keep in cache for 5 minutes
  });

  // Prefetch next frames for smoother playback
  useEffect(() => {
    if (!framesData?.frames || !isPlaying || !jobId) return;

    // Prefetch next 5 frames for both left and right cameras
    for (let i = 1; i <= 5; i++) {
      const nextIndex = currentFrameIndex + i;
      if (nextIndex < framesData.frames.length) {
        const nextFrameId = framesData.frames[nextIndex].frame_id;
        // Prefetch left image
        const imgLeft = new Image();
        imgLeft.src = `/api/data/jobs/${jobId}/frames/${nextFrameId}/image/left`;
        // Prefetch right image
        const imgRight = new Image();
        imgRight.src = `/api/data/jobs/${jobId}/frames/${nextFrameId}/image/right`;
      }
    }
  }, [currentFrameIndex, isPlaying, framesData, jobId]);

  // Update store when frames load
  useEffect(() => {
    if (framesData) {
      const thumbnails = framesData.frames.map((f) => ({
        frame_id: f.frame_id,
        sequence_index: f.sequence_index,
        svo2_frame_index: f.svo2_frame_index,
        thumbnail_url: `/api/data/jobs/${jobId}/frames/${f.frame_id}/image/left`,
        annotation_count: f.detection_count,
      }));
      setFrames(thumbnails, framesData.total);
    }
  }, [framesData, jobId, setFrames]);

  // Reset on unmount
  useEffect(() => {
    return () => resetAll();
  }, [resetAll]);

  // Filter annotations based on excluded classes
  const filteredAnnotations = useMemo(() => {
    if (!frameDetail?.annotations) return [];
    return frameDetail.annotations.filter(
      (ann) => !excludedClasses.has(ann.class_name)
    );
  }, [frameDetail?.annotations, excludedClasses]);

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-[1800px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-blue-600 text-white text-sm font-medium rounded-full">
              Step 3
            </span>
            <h1 className="text-2xl font-bold text-white">Review & Filter</h1>
          </div>
          <p className="text-gray-400">
            Review processed data, filter objects and frames, then export training datasets.
          </p>
        </div>

        {/* Job Selection / Selected Job Header */}
        {showJobSelector || !jobId ? (
          /* Job Selection Grid */
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-white">
                Select a Completed Job to Review
              </h2>
              <span className="text-sm text-gray-400">
                {completedJobs.length} completed job{completedJobs.length !== 1 ? 's' : ''}
              </span>
            </div>

            {jobsLoading ? (
              <div className="text-center py-12">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
                <p className="mt-3 text-gray-400">Loading jobs...</p>
              </div>
            ) : completedJobs.length === 0 ? (
              <div className="text-center py-16 bg-gray-800/50 rounded-lg">
                <CheckCircleIcon className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <p className="text-lg text-gray-400">No completed jobs yet</p>
                <p className="text-sm text-gray-500 mt-2">
                  Complete processing jobs in Step 2 to review them here
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {completedJobs.map((job: JobResponse) => {
                  const dataset = job.dataset_id ? datasetMap.get(job.dataset_id) : null;
                  const isSelected = job.id === jobId;

                  return (
                    <div
                      key={job.id}
                      onClick={() => {
                        setJobId(job.id);
                        setShowJobSelector(false);
                      }}
                      className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all hover:bg-gray-750 border-2 ${
                        isSelected
                          ? 'border-blue-500 ring-2 ring-blue-500/30'
                          : 'border-transparent hover:border-gray-600'
                      }`}
                    >
                      {/* Job Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-white truncate" title={job.name}>
                            {job.name}
                          </h3>
                          {dataset && (
                            <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
                              <FolderIcon className="w-3 h-3" />
                              <span className="truncate">{dataset.name}</span>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 px-2 py-1 bg-green-600/20 text-green-400 rounded text-xs">
                          <CheckCircleIcon className="w-3.5 h-3.5" />
                          <span>Completed</span>
                        </div>
                      </div>

                      {/* Stats Grid */}
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div className="flex items-center gap-2 text-sm">
                          <FilmIcon className="w-4 h-4 text-blue-400" />
                          <span className="text-gray-300">
                            {job.total_frames ?? 0} frames
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <CubeIcon className="w-4 h-4 text-purple-400" />
                          <span className="text-gray-300">
                            {job.total_detections ?? 0} detections
                          </span>
                        </div>
                      </div>

                      {/* Object Classes */}
                      {job.config?.object_class_ids && job.config.object_class_ids.length > 0 && (
                        <div className="mb-3">
                          <div className="flex flex-wrap gap-1">
                            {job.config.object_class_ids.slice(0, 4).map((cls: string, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs"
                              >
                                {cls}
                              </span>
                            ))}
                            {job.config.object_class_ids.length > 4 && (
                              <span className="px-2 py-0.5 bg-gray-700 text-gray-400 rounded text-xs">
                                +{job.config.object_class_ids.length - 4} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Time Info */}
                      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-700">
                        <div className="flex items-center gap-1">
                          <ClockIcon className="w-3.5 h-3.5" />
                          <span>Completed {job.completed_at ? formatRelativeTime(job.completed_at) : 'N/A'}</span>
                        </div>
                        {job.started_at && job.completed_at && (
                          <span>Duration: {formatDuration(job.started_at, job.completed_at)}</span>
                        )}
                      </div>

                      {/* Select indicator */}
                      <div className="flex items-center justify-end mt-3 text-sm text-blue-400">
                        <span>Select to review</span>
                        <ChevronRightIcon className="w-4 h-4 ml-1" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          /* Selected Job Header Bar */
          <div className="mb-6 bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setShowJobSelector(true)}
                  className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Change Job
                </button>
                <div className="border-l border-gray-600 pl-4">
                  <h2 className="font-medium text-white">{selectedJob?.name}</h2>
                  <div className="flex items-center gap-4 text-sm text-gray-400 mt-1">
                    <span className="flex items-center gap-1">
                      <FilmIcon className="w-4 h-4" />
                      {selectedJob?.total_frames ?? 0} frames
                    </span>
                    <span className="flex items-center gap-1">
                      <CubeIcon className="w-4 h-4" />
                      {selectedJob?.total_detections ?? 0} detections
                    </span>
                    {selectedJob?.dataset_id && datasetMap.get(selectedJob.dataset_id) && (
                      <span className="flex items-center gap-1">
                        <FolderIcon className="w-4 h-4" />
                        {datasetMap.get(selectedJob.dataset_id)?.name}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={openExportModal}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Create Training Dataset
              </button>
            </div>
          </div>
        )}

        {showJobSelector || !jobId ? null : framesLoading ? (
          <div className="text-center py-20">
            <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
            <p className="mt-4 text-gray-400">Loading frames...</p>
          </div>
        ) : (
          <div className="grid grid-cols-12 gap-6">
            {/* Left panel - Object filtering */}
            <div className="col-span-3">
              <ObjectFilterPanel
                classStats={annotationStats?.classes ?? []}
                isLoading={statsLoading}
              />
            </div>

            {/* Center - Frame viewer */}
            <div className="col-span-6 space-y-4">
              {/* Frame display with camera tabs */}
              <div className="bg-gray-800 rounded-lg overflow-hidden">
                {/* Camera tabs */}
                <div className="flex border-b border-gray-700">
                  <button
                    onClick={() => setCameraView('left')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      cameraView === 'left'
                        ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-700/50'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
                    }`}
                  >
                    <EyeIcon className="w-4 h-4 inline mr-1.5" />
                    Left Camera
                  </button>
                  <button
                    onClick={() => setCameraView('right')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      cameraView === 'right'
                        ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-700/50'
                        : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
                    }`}
                  >
                    <EyeIcon className="w-4 h-4 inline mr-1.5" />
                    Right Camera
                  </button>
                </div>

                {frameDetail ? (
                  <div className="aspect-video relative">
                    <AnnotatedImage
                      imageUrl={`/api/data/jobs/${jobId}/frames/${currentFrameId}/image/${cameraView}`}
                      annotations={filteredAnnotations}
                      showMasks={true}
                      selectedAnnotationId={null}
                    />
                    {/* Frame info overlay */}
                    <div className="absolute top-4 left-4 bg-black/60 px-3 py-1 rounded text-sm text-white">
                      Frame {currentFrameIndex + 1} / {totalFrames}
                      {frameDetail.svo2_frame_index !== undefined && (
                        <span className="text-gray-400 ml-2">
                          (SVO2: {frameDetail.svo2_frame_index})
                        </span>
                      )}
                    </div>
                    {/* Annotation count */}
                    <div className="absolute top-4 right-4 bg-black/60 px-3 py-1 rounded text-sm">
                      <span className="text-green-400">{filteredAnnotations.length}</span>
                      <span className="text-gray-400"> / {frameDetail.annotations?.length ?? 0} objects</span>
                    </div>
                  </div>
                ) : (
                  <div className="aspect-video bg-gray-700 flex items-center justify-center">
                    <span className="text-gray-400">No frame selected</span>
                  </div>
                )}
              </div>

              {/* Depth Map and IMU Data - Always visible */}
              <div className="grid grid-cols-2 gap-4">
                {/* Depth Map */}
                <div className="bg-gray-800 rounded-lg overflow-hidden">
                  <div className="px-3 py-2 border-b border-gray-700">
                    <h3 className="text-sm font-medium text-gray-300">Depth Map</h3>
                  </div>
                  {frameDetail?.depth_url ? (
                    <div className="aspect-video relative">
                      <img
                        src={`/api/data/jobs/${jobId}/frames/${currentFrameId}/image/depth`}
                        alt="Depth map"
                        className="w-full h-full object-contain bg-gray-900"
                      />
                    </div>
                  ) : (
                    <div className="aspect-video bg-gray-700 flex items-center justify-center">
                      <span className="text-gray-500 text-sm">No depth data</span>
                    </div>
                  )}
                </div>

                {/* IMU Data Panel */}
                <div className="bg-gray-800 rounded-lg overflow-hidden">
                  <div className="px-3 py-2 border-b border-gray-700">
                    <h3 className="text-sm font-medium text-gray-300">IMU / Sensor Data</h3>
                  </div>
                  <div className="p-3">
                    {frameDetail?.metadata ? (
                      <IMUDisplay metadata={frameDetail.metadata} />
                    ) : (
                      <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
                        No IMU data available
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Playback controls */}
              <PlaybackControls disabled={!jobId || totalFrames === 0} />

              {/* Annotations list */}
              {frameDetail && filteredAnnotations.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">
                    Detected Objects ({filteredAnnotations.length})
                  </h3>
                  <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                    {filteredAnnotations.map((ann) => (
                      <div
                        key={ann.id}
                        className="flex items-center gap-2 px-2 py-1 bg-gray-700 rounded text-sm"
                      >
                        <div
                          className="w-3 h-3 rounded"
                          style={{ backgroundColor: ann.class_color }}
                        />
                        <span className="text-white">{ann.class_name}</span>
                        <span className="text-gray-400 text-xs ml-auto">
                          {(ann.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right panel - Frame diversity */}
            <div className="col-span-3">
              <FrameDiversityPanel jobId={jobId} />
            </div>
          </div>
        )}

        {/* Export modal */}
        {isExportModalOpen && jobId && (
          <TrainingDatasetModal jobId={jobId} onClose={closeExportModal} />
        )}
      </div>
    </div>
  );
};

export default ReviewPage;
