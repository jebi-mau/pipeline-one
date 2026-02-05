/**
 * Pipeline One - Job Actions component
 */

import { PlayIcon, PauseIcon, StopIcon, TrashIcon, ArrowPathIcon, DocumentChartBarIcon } from '@heroicons/react/24/outline';
import { useStartJob, usePauseJob, useResumeJob, useCancelJob, useRestartJob, useDeleteJob } from '../../hooks/useJobs';
import { LoadingSpinner } from '../common/LoadingSpinner';
import type { JobStatus } from '../../types/job';

interface JobActionsProps {
  jobId: string;
  status: JobStatus;
  onDeleted?: () => void;
  onReport?: () => void;
  showDelete?: boolean;
  showReport?: boolean;
  size?: 'sm' | 'md';
}

export function JobActions({ jobId, status, onDeleted, onReport, showDelete = false, showReport = false, size = 'sm' }: JobActionsProps) {
  const startJob = useStartJob();
  const pauseJob = usePauseJob();
  const resumeJob = useResumeJob();
  const cancelJob = useCancelJob();
  const restartJob = useRestartJob();
  const deleteJob = useDeleteJob();

  const isLoading = startJob.isPending || pauseJob.isPending || resumeJob.isPending || cancelJob.isPending || restartJob.isPending || deleteJob.isPending;

  const iconSize = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';
  const buttonBase = size === 'sm'
    ? 'p-1.5 rounded-lg transition-colors'
    : 'p-2 rounded-lg transition-colors';

  const handleStart = () => startJob.mutate(jobId);
  const handlePause = () => pauseJob.mutate(jobId);
  const handleResume = () => resumeJob.mutate(jobId);
  const handleCancel = () => cancelJob.mutate(jobId);
  const handleRestart = () => restartJob.mutate(jobId);
  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this job?')) {
      await deleteJob.mutateAsync(jobId);
      onDeleted?.();
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center">
        <LoadingSpinner size="sm" />
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-1">
      {status === 'pending' && (
        <button
          onClick={handleStart}
          className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
          title="Start Job"
          aria-label="Start job processing"
        >
          <PlayIcon className={iconSize} aria-hidden="true" />
        </button>
      )}

      {status === 'running' && (
        <>
          <button
            onClick={handlePause}
            className={`${buttonBase} bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/40 focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
            title="Pause Job"
            aria-label="Pause job processing"
          >
            <PauseIcon className={iconSize} aria-hidden="true" />
          </button>
          <button
            onClick={handleCancel}
            className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
            title="Cancel Job"
            aria-label="Cancel job processing"
          >
            <StopIcon className={iconSize} aria-hidden="true" />
          </button>
        </>
      )}

      {status === 'paused' && (
        <>
          <button
            onClick={handleResume}
            className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
            title="Resume Job"
            aria-label="Resume job processing"
          >
            <PlayIcon className={iconSize} aria-hidden="true" />
          </button>
          <button
            onClick={handleCancel}
            className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
            title="Cancel Job"
            aria-label="Cancel job processing"
          >
            <StopIcon className={iconSize} aria-hidden="true" />
          </button>
        </>
      )}

      {(status === 'failed' || status === 'cancelled') && (
        <button
          onClick={handleRestart}
          className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
          title="Restart Job"
          aria-label="Restart job from beginning"
        >
          <ArrowPathIcon className={iconSize} aria-hidden="true" />
        </button>
      )}

      {showReport && (
        <button
          onClick={onReport}
          className={`${buttonBase} bg-primary-600/20 text-primary-400 hover:bg-primary-600/40 focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
          title="View Report"
          aria-label="View job report"
        >
          <DocumentChartBarIcon className={iconSize} aria-hidden="true" />
        </button>
      )}

      {showDelete && (status === 'completed' || status === 'failed' || status === 'cancelled') && (
        <button
          onClick={handleDelete}
          className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-secondary-900`}
          title="Delete Job"
          aria-label="Delete job and its output files"
        >
          <TrashIcon className={iconSize} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
