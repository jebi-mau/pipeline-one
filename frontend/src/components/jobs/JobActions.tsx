/**
 * Shalom - Job Actions component
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
          className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40`}
          title="Start Job"
        >
          <PlayIcon className={iconSize} />
        </button>
      )}

      {status === 'running' && (
        <>
          <button
            onClick={handlePause}
            className={`${buttonBase} bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/40`}
            title="Pause Job"
          >
            <PauseIcon className={iconSize} />
          </button>
          <button
            onClick={handleCancel}
            className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40`}
            title="Cancel Job"
          >
            <StopIcon className={iconSize} />
          </button>
        </>
      )}

      {status === 'paused' && (
        <>
          <button
            onClick={handleResume}
            className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40`}
            title="Resume Job"
          >
            <PlayIcon className={iconSize} />
          </button>
          <button
            onClick={handleCancel}
            className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40`}
            title="Cancel Job"
          >
            <StopIcon className={iconSize} />
          </button>
        </>
      )}

      {(status === 'failed' || status === 'cancelled') && (
        <button
          onClick={handleRestart}
          className={`${buttonBase} bg-green-600/20 text-green-400 hover:bg-green-600/40`}
          title="Restart Job"
        >
          <ArrowPathIcon className={iconSize} />
        </button>
      )}

      {showReport && (
        <button
          onClick={onReport}
          className={`${buttonBase} bg-primary-600/20 text-primary-400 hover:bg-primary-600/40`}
          title="View Report"
        >
          <DocumentChartBarIcon className={iconSize} />
        </button>
      )}

      {showDelete && (status === 'completed' || status === 'failed' || status === 'cancelled') && (
        <button
          onClick={handleDelete}
          className={`${buttonBase} bg-red-600/20 text-red-400 hover:bg-red-600/40`}
          title="Delete Job"
        >
          <TrashIcon className={iconSize} />
        </button>
      )}
    </div>
  );
}
