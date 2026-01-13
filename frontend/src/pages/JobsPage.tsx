/**
 * JobsPage - Step 2 of the pipeline: Process SVO2 files with extraction and detection
 */

import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  InformationCircleIcon,
  DocumentChartBarIcon,
  ArrowRightIcon,
  CpuChipIcon,
  PlayIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useJobs } from '../hooks/useJobs';
import { useDatasets } from '../hooks/useDatasets';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';
import { CreateJobModal } from '../components/jobs/CreateJobModal';
import { JobInfoModal } from '../components/jobs/JobInfoModal';
import { JobReportModal } from '../components/jobs/JobReportModal';
import { JobActions } from '../components/jobs/JobActions';
import { StageProgressBar } from '../components/jobs/StageProgressBar';
import { ETADisplay } from '../components/jobs/ETADisplay';
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

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  pending: ClockIcon,
  running: PlayIcon,
  completed: CheckCircleIcon,
  failed: ExclamationTriangleIcon,
};

interface LocationState {
  datasetId?: string;
  openCreateModal?: boolean;
}

export default function JobsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const locationState = location.state as LocationState | null;

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [preselectedDatasetId, setPreselectedDatasetId] = useState<string | null>(null);
  const { data: jobsData, isLoading, isError, error, refetch } = useJobs();
  const { data: datasetsData } = useDatasets();

  // Auto-open modal if navigated from datasets page
  useEffect(() => {
    if (locationState?.openCreateModal) {
      setIsCreateModalOpen(true);
      if (locationState.datasetId) {
        setPreselectedDatasetId(locationState.datasetId);
      }
      // Clear the state to prevent reopening on refresh
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [locationState, navigate, location.pathname]);

  const handleShowInfo = (job: Job) => {
    setSelectedJob(job);
    setIsInfoModalOpen(true);
  };

  const handleShowReport = (job: Job) => {
    setSelectedJob(job);
    setIsReportModalOpen(true);
  };

  const jobs = jobsData?.jobs ?? [];
  const datasets = datasetsData?.datasets ?? [];
  const readyDatasets = datasets.filter((d) => d.status === 'ready');
  const runningJobs = jobs.filter((j: Job) => j.status === 'running');
  const completedJobs = jobs.filter((j: Job) => j.status === 'completed');

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
      {/* Step Instructions */}
      <div className="bg-primary-900/20 border border-primary-700/50 rounded-xl p-4">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-600/30 border border-primary-500 flex items-center justify-center">
            <span className="text-lg font-bold text-primary-400">2</span>
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-secondary-100 mb-1">
              Process & Detect Objects
            </h2>
            <p className="text-sm text-secondary-400 mb-3">
              Create processing jobs to extract frames from SVO2 files and run SAM3 object
              detection. Each job processes a dataset through the extraction, segmentation,
              and tracking pipeline.
            </p>
            <div className="flex items-center gap-6 text-xs text-secondary-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Extract: Frames, depth, sensors
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-purple-500" />
                Segment: SAM3 detection
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                Track: Object IDs across frames
              </span>
            </div>
          </div>
          {completedJobs.length > 0 && (
            <Link
              to="/data"
              className="btn-primary flex items-center gap-2 flex-shrink-0"
            >
              Review Results
              <ArrowRightIcon className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <QuickStat
          icon={CpuChipIcon}
          label="Ready Datasets"
          value={readyDatasets.length}
          href="/datasets"
          highlight={readyDatasets.length > 0 && jobs.length === 0}
        />
        <QuickStat
          icon={PlayIcon}
          label="Running Jobs"
          value={runningJobs.length}
          highlight={runningJobs.length > 0}
        />
        <QuickStat
          icon={CheckCircleIcon}
          label="Completed"
          value={completedJobs.length}
          valueColor="text-green-400"
        />
        <QuickStat
          icon={ExclamationTriangleIcon}
          label="Failed"
          value={jobs.filter((j: Job) => j.status === 'failed').length}
          valueColor="text-red-400"
        />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-100">Processing Jobs</h1>
          <p className="text-sm text-secondary-400 mt-1">
            {jobs.length} job{jobs.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="btn-primary"
          disabled={readyDatasets.length === 0}
          title={readyDatasets.length === 0 ? 'No ready datasets available' : ''}
        >
          <PlusIcon className="w-5 h-5 mr-2" />
          New Job
        </button>
      </div>

      {/* No Datasets Warning */}
      {readyDatasets.length === 0 && (
        <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <ExclamationTriangleIcon className="w-6 h-6 text-yellow-500" />
            <div>
              <p className="text-sm font-medium text-yellow-300">
                No datasets ready for processing
              </p>
              <p className="text-xs text-yellow-400 mt-1">
                Go to Step 1 (Datasets) to create and prepare a dataset before creating jobs.
              </p>
            </div>
            <Link to="/datasets" className="btn-secondary ml-auto text-sm">
              Go to Datasets
            </Link>
          </div>
        </div>
      )}

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <EmptyState
          hasReadyDatasets={readyDatasets.length > 0}
          onCreateClick={() => setIsCreateModalOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          {/* Running Jobs Section */}
          {runningJobs.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-secondary-400 uppercase tracking-wider">
                Currently Running
              </h3>
              <div className="grid gap-3">
                {runningJobs.map((job: Job) => (
                  <JobCard key={job.id} job={job} expanded />
                ))}
              </div>
            </div>
          )}

          {/* All Jobs Table */}
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-secondary-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Job
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Pipeline Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    Frames
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-300 uppercase tracking-wider">
                    ETA
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
                {jobs.map((job: Job) => {
                  const StatusIcon = statusIcons[job.status] || ClockIcon;
                  return (
                    <tr key={job.id} className="hover:bg-secondary-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link
                          to={`/jobs/${job.id}`}
                          className="flex items-center gap-3 group"
                        >
                          <StatusIcon
                            className={`w-5 h-5 ${
                              job.status === 'running'
                                ? 'text-blue-400 animate-pulse'
                                : job.status === 'completed'
                                ? 'text-green-400'
                                : job.status === 'failed'
                                ? 'text-red-400'
                                : 'text-secondary-400'
                            }`}
                          />
                          <div>
                            <span className="text-sm font-medium text-secondary-100 group-hover:text-primary-400 transition-colors">
                              {job.name}
                            </span>
                            {job.current_stage_name && job.status === 'running' && (
                              <span className="block text-xs text-secondary-500">
                                {job.current_stage_name}
                              </span>
                            )}
                          </div>
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
                      <td className="px-6 py-4 w-56">
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
                        {job.processed_frames?.toLocaleString() || 0} /{' '}
                        {job.total_frames?.toLocaleString() || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {job.status === 'running' || job.status === 'paused' ? (
                          <ETADisplay totalEta={job.eta_seconds} compact />
                        ) : (
                          <span className="text-secondary-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-400">
                        {new Date(job.created_at).toLocaleDateString()}
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
                          {job.status === 'completed' && (
                            <button
                              onClick={() => handleShowReport(job)}
                              className="p-1.5 rounded-lg transition-colors bg-primary-600/20 text-primary-400 hover:bg-primary-600/40"
                              title="View Report"
                            >
                              <DocumentChartBarIcon className="w-4 h-4" />
                            </button>
                          )}
                          <JobActions jobId={job.id} status={job.status} showDelete />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
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
        onClose={() => {
          setIsCreateModalOpen(false);
          setPreselectedDatasetId(null);
        }}
        preselectedDatasetId={preselectedDatasetId}
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

// Quick Stat Component
function QuickStat({
  icon: Icon,
  label,
  value,
  href,
  highlight,
  valueColor,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  href?: string;
  highlight?: boolean;
  valueColor?: string;
}) {
  const content = (
    <div
      className={`card p-4 ${
        highlight ? 'border-primary-500/50 bg-primary-900/20' : ''
      } ${href ? 'hover:bg-secondary-700/50 transition-colors cursor-pointer' : ''}`}
    >
      <div className="flex items-center gap-3">
        <Icon
          className={`w-6 h-6 ${highlight ? 'text-primary-400' : 'text-secondary-400'}`}
        />
        <div>
          <p className={`text-xl font-bold ${valueColor || 'text-secondary-100'}`}>
            {value}
          </p>
          <p className="text-xs text-secondary-400">{label}</p>
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }
  return content;
}

// Job Card for expanded view of running jobs
function JobCard({
  job,
  expanded,
}: {
  job: Job;
  expanded?: boolean;
}) {
  if (!expanded) return null;

  return (
    <div className="card p-4 border-blue-500/50 bg-blue-900/10">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-blue-600/20 flex items-center justify-center">
          <CpuChipIcon className="w-6 h-6 text-blue-400 animate-pulse" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <Link
              to={`/jobs/${job.id}`}
              className="font-semibold text-secondary-100 hover:text-primary-400"
            >
              {job.name}
            </Link>
            <span className="text-xs text-blue-400 bg-blue-600/20 px-2 py-1 rounded">
              {job.current_stage_name || 'Processing'}
            </span>
          </div>
          <StageProgressBar
            stages={job.stages_to_run || ALL_PIPELINE_STAGES}
            currentStage={job.current_stage || 0}
            currentStageName={job.current_stage_name}
            progress={job.progress || 0}
            jobStatus={job.status}
          />
          <div className="flex items-center justify-between mt-3 text-sm">
            <span className="text-secondary-400">
              {job.processed_frames?.toLocaleString() || 0} /{' '}
              {job.total_frames?.toLocaleString() || '-'} frames
            </span>
            <div className="flex items-center gap-4">
              <ETADisplay totalEta={job.eta_seconds} compact />
              <JobActions jobId={job.id} status={job.status} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Empty State Component
function EmptyState({
  hasReadyDatasets,
  onCreateClick,
}: {
  hasReadyDatasets: boolean;
  onCreateClick: () => void;
}) {
  return (
    <div className="card p-12 text-center">
      <div className="max-w-md mx-auto">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-primary-600/20 flex items-center justify-center">
          <CpuChipIcon className="w-10 h-10 text-primary-400" />
        </div>
        <h2 className="text-xl font-bold text-secondary-100 mb-2">
          No Processing Jobs Yet
        </h2>
        <p className="text-secondary-400 mb-6">
          {hasReadyDatasets
            ? 'Create a processing job to extract frames and detect objects from your SVO2 files.'
            : 'First, create and prepare a dataset in Step 1, then come back here to process it.'}
        </p>

        {hasReadyDatasets ? (
          <button onClick={onCreateClick} className="btn-primary">
            <PlusIcon className="w-5 h-5 mr-2" />
            Create Your First Job
          </button>
        ) : (
          <Link to="/datasets" className="btn-primary inline-flex items-center">
            Go to Step 1: Datasets
            <ArrowRightIcon className="w-4 h-4 ml-2" />
          </Link>
        )}
      </div>
    </div>
  );
}
