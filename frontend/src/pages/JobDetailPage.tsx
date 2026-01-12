/**
 * Shalom - Job Detail page with real data
 */

import { useParams, Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { useJob } from '../hooks/useJobs';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { JobActions } from '../components/jobs/JobActions';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  running: 'bg-blue-500',
  paused: 'bg-orange-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
};

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { data: job, isLoading, isError, error, refetch } = useJob(jobId || '');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError || !job) {
    return (
      <ErrorMessage
        title="Failed to load job"
        message={error?.message || 'Job not found'}
        onRetry={() => refetch()}
      />
    );
  }

  const isActive = job.status === 'running' || job.status === 'paused';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/jobs" className="text-secondary-400 hover:text-secondary-100">
            <ArrowLeftIcon className="w-5 h-5" />
          </Link>
          <h1 className="text-2xl font-bold text-secondary-100">{job.name}</h1>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              statusColors[job.status] || 'bg-gray-500'
            } text-white`}
          >
            {job.status}
          </span>
        </div>
        <JobActions jobId={job.id} status={job.status} size="md" />
      </div>

      {/* Progress */}
      {isActive && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Progress</h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm text-secondary-400 mb-1">
                <span>Processing</span>
                <span>{job.progress?.toFixed(1) || 0}%</span>
              </div>
              <div className="w-full bg-secondary-600 rounded-full h-3">
                <div
                  className="bg-primary-500 h-3 rounded-full transition-all"
                  style={{ width: `${job.progress || 0}%` }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-secondary-100">
                  {job.processed_frames?.toLocaleString() || 0}
                </p>
                <p className="text-sm text-secondary-400">Frames Processed</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-secondary-100">
                  {job.total_frames?.toLocaleString() || '-'}
                </p>
                <p className="text-sm text-secondary-400">Total Frames</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-secondary-100">
                  {job.current_stage || '-'}
                </p>
                <p className="text-sm text-secondary-400">Current Stage</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {job.status === 'failed' && job.error_message && (
        <div className="card p-6 border border-red-500/50">
          <h2 className="text-lg font-medium text-red-400 mb-2">Error</h2>
          <pre className="text-sm text-secondary-300 bg-secondary-900 p-4 rounded overflow-x-auto">
            {job.error_message}
          </pre>
        </div>
      )}

      {/* Job Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Configuration */}
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Configuration</h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-secondary-400">Created</dt>
              <dd className="text-secondary-100">
                {new Date(job.created_at).toLocaleString()}
              </dd>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Started</dt>
                <dd className="text-secondary-100">
                  {new Date(job.started_at).toLocaleString()}
                </dd>
              </div>
            )}
            {job.completed_at && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Completed</dt>
                <dd className="text-secondary-100">
                  {new Date(job.completed_at).toLocaleString()}
                </dd>
              </div>
            )}
            {job.config?.sam3_confidence !== undefined && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Confidence Threshold</dt>
                <dd className="text-secondary-100">{job.config.sam3_confidence}</dd>
              </div>
            )}
            {job.config?.batch_size !== undefined && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Batch Size</dt>
                <dd className="text-secondary-100">{job.config.batch_size}</dd>
              </div>
            )}
            {job.config?.frame_skip !== undefined && (
              <div className="flex justify-between">
                <dt className="text-secondary-400">Frame Skip</dt>
                <dd className="text-secondary-100">{job.config.frame_skip}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Input Files */}
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Input Files</h2>
          {job.input_files && job.input_files.length > 0 ? (
            <ul className="space-y-2">
              {job.input_files.map((file, index) => (
                <li key={index} className="text-sm text-secondary-300 truncate">
                  {file}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-secondary-400">No input files</p>
          )}
        </div>

        {/* Object Classes */}
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Object Classes</h2>
          {job.object_classes && job.object_classes.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {job.object_classes.map((cls, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-secondary-700 text-secondary-200 rounded-full text-sm"
                >
                  {cls}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-secondary-400">No object classes specified</p>
          )}
        </div>

        {/* Output */}
        {job.output_directory && (
          <div className="card p-6">
            <h2 className="text-lg font-medium text-secondary-100 mb-4">Output</h2>
            <dl className="space-y-3">
              <div>
                <dt className="text-secondary-400 text-sm">Output Directory</dt>
                <dd className="text-secondary-100 text-sm truncate">
                  {job.output_directory}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </div>

      {/* Results Section (for completed jobs) */}
      {job.status === 'completed' && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Results</h2>
          <p className="text-secondary-400">
            Job completed successfully. Results are available in the output directory.
          </p>
          <div className="mt-4 flex space-x-3">
            <button className="btn-secondary">Download KITTI Format</button>
            <button className="btn-secondary">View 3D Visualization</button>
          </div>
        </div>
      )}
    </div>
  );
}
