/**
 * Shalom - Jobs page with real data and create job modal
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PlusIcon, InformationCircleIcon, DocumentChartBarIcon } from '@heroicons/react/24/outline';
import { useJobs } from '../hooks/useJobs';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { CreateJobModal } from '../components/jobs/CreateJobModal';
import { JobInfoModal } from '../components/jobs/JobInfoModal';
import { JobReportModal } from '../components/jobs/JobReportModal';
import { JobActions } from '../components/jobs/JobActions';
import { StageProgressBar } from '../components/jobs/StageProgressBar';
import type { Job } from '../types/job';
import { ALL_PIPELINE_STAGES } from '../types/job';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500',
  running: 'bg-blue-500',
  paused: 'bg-orange-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
};

export default function JobsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const { data: jobsData, isLoading, isError, error, refetch } = useJobs();

  const handleShowInfo = (job: Job) => {
    setSelectedJob(job);
    setIsInfoModalOpen(true);
  };

  const handleShowReport = (job: Job) => {
    setSelectedJob(job);
    setIsReportModalOpen(true);
  };

  const jobs = jobsData?.jobs ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage
        title="Failed to load jobs"
        message={error?.message || 'An error occurred while fetching jobs'}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-secondary-100">Processing Jobs</h1>
        <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary">
          <PlusIcon className="w-5 h-5 mr-2" />
          New Job
        </button>
      </div>

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-secondary-400 mb-4">No jobs yet. Create your first processing job.</p>
          <button onClick={() => setIsCreateModalOpen(true)} className="btn-primary">
            <PlusIcon className="w-5 h-5 mr-2" />
            Create Job
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-secondary-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Progress
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Frames
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-700">
              {jobs.map((job: Job) => (
                <tr
                  key={job.id}
                  className="hover:bg-secondary-700/50"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link
                      to={`/jobs/${job.id}`}
                      className="text-sm font-medium text-secondary-100 hover:text-primary-400"
                    >
                      {job.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        statusColors[job.status] || 'bg-gray-500'
                      } text-white`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 w-48">
                    <StageProgressBar
                      stages={job.stages_to_run || ALL_PIPELINE_STAGES}
                      currentStage={job.current_stage || 0}
                      currentStageName={job.current_stage_name}
                      progress={job.progress || 0}
                      jobStatus={job.status}
                      compact
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-300">
                    {job.processed_frames?.toLocaleString() || 0} / {job.total_frames?.toLocaleString() || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-400">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleShowInfo(job)}
                        className="p-1.5 rounded-lg transition-colors bg-secondary-600/50 text-secondary-300 hover:bg-secondary-600 hover:text-secondary-100"
                        title="View Job Details"
                      >
                        <InformationCircleIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleShowReport(job)}
                        className="p-1.5 rounded-lg transition-colors bg-primary-600/20 text-primary-400 hover:bg-primary-600/40"
                        title="View Report"
                      >
                        <DocumentChartBarIcon className="w-4 h-4" />
                      </button>
                      <JobActions jobId={job.id} status={job.status} showDelete />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Info */}
      {jobsData && jobsData.total > 0 && (
        <div className="text-sm text-secondary-400 text-center">
          Showing {jobs.length} of {jobsData.total} jobs
        </div>
      )}

      {/* Create Job Modal */}
      <CreateJobModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {/* Job Info Modal */}
      <JobInfoModal
        isOpen={isInfoModalOpen}
        onClose={() => {
          setIsInfoModalOpen(false);
          setSelectedJob(null);
        }}
        job={selectedJob}
      />

      {/* Job Report Modal */}
      <JobReportModal
        isOpen={isReportModalOpen}
        onClose={() => {
          setIsReportModalOpen(false);
          setSelectedJob(null);
        }}
        job={selectedJob}
      />
    </div>
  );
}
