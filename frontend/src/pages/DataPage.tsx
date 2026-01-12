/**
 * Shalom - Data Explorer page for browsing extracted frame data
 */

import { useState, useMemo } from 'react';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  TableCellsIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline';
import { useJobs } from '../hooks/useJobs';
import { useDataSummary, useFrameList } from '../hooks/useData';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { DataSummaryPanel } from '../components/data/DataSummaryPanel';
import { FrameGrid } from '../components/data/FrameGrid';
import { CorrelationTable } from '../components/data/CorrelationTable';
import { FrameViewer } from '../components/data/FrameViewer';
import type { Job } from '../types/job';

type ViewMode = 'grid' | 'table';

export default function DataPage() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [page, setPage] = useState(0);
  const [selectedFrameId, setSelectedFrameId] = useState<string | null>(null);
  const pageSize = 24;

  // Fetch completed jobs for the selector
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ status: 'completed' });

  // Fetch data summary for selected job
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useDataSummary(selectedJobId || undefined);

  // Fetch frames for selected job
  const {
    data: framesData,
    isLoading: framesLoading,
    error: framesError,
  } = useFrameList(selectedJobId || undefined, {
    limit: pageSize,
    offset: page * pageSize,
  });

  // Filter jobs that have output
  const completedJobs = useMemo(() => {
    const jobs = jobsData?.jobs || [];
    return jobs.filter((job: Job) => job.status === 'completed');
  }, [jobsData]);

  // Auto-select first job if none selected
  const effectiveJobId = selectedJobId || (completedJobs.length > 0 ? completedJobs[0].id : null);

  // Handle job selection
  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId);
    setPage(0);
    setSelectedFrameId(null);
  };

  // Handle frame click
  const handleFrameClick = (frameId: string) => {
    setSelectedFrameId(frameId);
  };

  // Handle navigation in frame viewer
  const handleNavigateFrame = (direction: 'prev' | 'next') => {
    if (!framesData?.frames || !selectedFrameId) return;

    const currentIndex = framesData.frames.findIndex((f) => f.frame_id === selectedFrameId);
    if (currentIndex === -1) return;

    if (direction === 'prev' && currentIndex > 0) {
      setSelectedFrameId(framesData.frames[currentIndex - 1].frame_id);
    } else if (direction === 'next' && currentIndex < framesData.frames.length - 1) {
      setSelectedFrameId(framesData.frames[currentIndex + 1].frame_id);
    }
  };

  // Pagination
  const totalPages = framesData ? Math.ceil(framesData.total / pageSize) : 0;

  if (jobsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (completedJobs.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-secondary-100">Data Explorer</h1>
        <div className="card p-12 text-center">
          <p className="text-secondary-400 mb-4">
            No completed jobs with extracted data found.
          </p>
          <p className="text-sm text-secondary-500">
            Complete a processing job to explore its extracted frames and annotations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-secondary-100">Data Explorer</h1>
        <div className="flex items-center space-x-4">
          {/* Job Selector */}
          <select
            value={effectiveJobId || ''}
            onChange={(e) => handleJobSelect(e.target.value)}
            className="bg-secondary-700 border border-secondary-600 text-secondary-200 rounded-lg px-4 py-2 focus:ring-primary-500 focus:border-primary-500"
          >
            {completedJobs.map((job: Job) => (
              <option key={job.id} value={job.id}>
                {job.name}
              </option>
            ))}
          </select>

          {/* View Mode Toggle */}
          <div className="flex items-center bg-secondary-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-primary-600 text-white'
                  : 'text-secondary-400 hover:text-secondary-200'
              }`}
              title="Grid View"
            >
              <Squares2X2Icon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'table'
                  ? 'bg-primary-600 text-white'
                  : 'text-secondary-400 hover:text-secondary-200'
              }`}
              title="Table View"
            >
              <TableCellsIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Data Summary Sidebar */}
        <div className="col-span-3">
          {summaryLoading ? (
            <div className="card p-6 flex items-center justify-center">
              <LoadingSpinner size="md" />
            </div>
          ) : summaryError ? (
            <ErrorMessage title="Failed to load summary" message="Could not fetch data summary" />
          ) : summary ? (
            <DataSummaryPanel summary={summary} />
          ) : null}
        </div>

        {/* Frame Browser */}
        <div className="col-span-9">
          {framesLoading ? (
            <div className="card p-12 flex items-center justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : framesError ? (
            <ErrorMessage
              title="Failed to load frames"
              message="Could not fetch frame data"
            />
          ) : viewMode === 'grid' ? (
            <div className="space-y-4">
              <FrameGrid
                frames={framesData?.frames || []}
                jobId={effectiveJobId || ''}
                onFrameClick={handleFrameClick}
              />

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between">
                  <div className="text-sm text-secondary-400">
                    Showing {page * pageSize + 1} -{' '}
                    {Math.min((page + 1) * pageSize, framesData?.total || 0)} of{' '}
                    {framesData?.total || 0} frames
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="p-2 rounded-lg bg-secondary-700 text-secondary-300 hover:bg-secondary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeftIcon className="w-5 h-5" />
                    </button>
                    <span className="text-sm text-secondary-300">
                      Page {page + 1} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={page >= totalPages - 1}
                      className="p-2 rounded-lg bg-secondary-700 text-secondary-300 hover:bg-secondary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRightIcon className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <CorrelationTable jobId={effectiveJobId || ''} />
          )}
        </div>
      </div>

      {/* Frame Viewer Modal */}
      {selectedFrameId && effectiveJobId && (
        <FrameViewer
          isOpen={!!selectedFrameId}
          onClose={() => setSelectedFrameId(null)}
          jobId={effectiveJobId}
          frameId={selectedFrameId}
          onNavigate={handleNavigateFrame}
        />
      )}
    </div>
  );
}
