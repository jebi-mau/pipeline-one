/**
 * HomePage - Workflow-oriented dashboard for SVO2 → Training Dataset pipeline
 */

import { Link } from 'react-router-dom';
import {
  FolderPlusIcon,
  CpuChipIcon,
  TagIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useJobs } from '../hooks/useJobs';
import { useDatasets } from '../hooks/useDatasets';
import { useModelInfo } from '../hooks/useConfig';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  WorkflowPipeline,
  WorkflowStage,
  defaultWorkflowStages,
} from '../components/workflow/WorkflowPipeline';

export default function HomePage() {
  const { data: allJobsData, isLoading: jobsLoading } = useJobs({});
  const { data: runningJobsData } = useJobs({ status: 'running' });
  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets();
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo();

  // Extract arrays from response objects
  const allJobs = allJobsData?.jobs ?? [];
  const runningJobs = runningJobsData?.jobs ?? [];
  const datasets = datasetsData?.datasets ?? [];

  // Calculate workflow stage statuses based on actual data
  const getWorkflowStages = (): WorkflowStage[] => {
    const datasetCount = datasets.length;
    const completedJobs = allJobs.filter((j) => j.status === 'completed');
    const runningJobCount = runningJobs.length;

    // Determine pipeline progress based on completed jobs
    const hasDatasets = datasetCount > 0;
    const hasCompletedJobs = completedJobs.length > 0;

    return defaultWorkflowStages.map((stage) => {
      let status: WorkflowStage['status'] = 'pending';
      let stats: WorkflowStage['stats'] | undefined;

      switch (stage.id) {
        case 'import':
          status = hasDatasets ? 'completed' : 'available';
          stats = { label: 'Datasets', value: datasetCount };
          break;
        case 'extract':
          if (!hasDatasets) status = 'pending';
          else if (hasCompletedJobs) status = 'completed';
          else status = 'available';
          stats = {
            label: 'Completed Jobs',
            value: completedJobs.length,
          };
          break;
        case 'segment':
          if (!hasCompletedJobs) status = 'pending';
          else status = 'completed';
          stats = {
            label: 'Processed',
            value: completedJobs.length,
          };
          break;
        case 'track':
          if (!hasCompletedJobs) status = 'pending';
          else status = 'completed';
          stats = {
            label: 'Tracked',
            value: completedJobs.length,
          };
          break;
        case 'annotate':
          status = hasCompletedJobs ? 'available' : 'pending';
          break;
        case 'export':
          status = hasCompletedJobs ? 'available' : 'pending';
          break;
      }

      // Check if any related job is currently running
      if (runningJobCount > 0) {
        const runningStageNames = runningJobs.map((j) => j.current_stage_name).filter(Boolean);
        if (
          (stage.id === 'extract' && runningStageNames.some((s) => s?.includes('xtract'))) ||
          (stage.id === 'segment' && runningStageNames.some((s) => s?.includes('egment'))) ||
          (stage.id === 'track' && runningStageNames.some((s) => s?.includes('rack')))
        ) {
          status = 'in_progress';
        }
      }

      return { ...stage, status, stats };
    });
  };

  const workflowStages = getWorkflowStages();
  const activeJobsCount = runningJobs.length;
  const gpuAvailable = modelInfo?.gpu_available ?? false;

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-900/30 to-secondary-800 rounded-xl p-8">
        <div className="max-w-3xl">
          <h1 className="text-3xl font-bold text-secondary-100 mb-3">
            SVO2 → Training Dataset Pipeline
          </h1>
          <p className="text-secondary-300 mb-6">
            Transform ZED camera recordings into ML-ready training data. Follow the
            workflow below to extract frames, detect objects, track across time, and
            export in KITTI format.
          </p>
          <div className="flex gap-4">
            <Link
              to="/datasets"
              className="btn-primary inline-flex items-center gap-2"
            >
              <FolderPlusIcon className="w-5 h-5" />
              Start New Pipeline
            </Link>
            {activeJobsCount > 0 && (
              <Link
                to="/jobs"
                className="btn-secondary inline-flex items-center gap-2"
              >
                <PlayIcon className="w-5 h-5" />
                View Running Jobs ({activeJobsCount})
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Workflow Pipeline Visualization */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-secondary-100 mb-6">
          Pipeline Workflow
        </h2>
        {datasetsLoading || jobsLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <WorkflowPipeline stages={workflowStages} orientation="horizontal" />
        )}
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <QuickStatCard
          icon={FolderPlusIcon}
          label="Datasets"
          value={datasets.length}
          loading={datasetsLoading}
          href="/datasets"
        />
        <QuickStatCard
          icon={PlayIcon}
          label="Active Jobs"
          value={activeJobsCount}
          loading={jobsLoading}
          href="/jobs"
          highlight={activeJobsCount > 0}
        />
        <QuickStatCard
          icon={CheckCircleIcon}
          label="Completed Jobs"
          value={allJobs.filter((j) => j.status === 'completed').length}
          loading={jobsLoading}
          href="/jobs?status=completed"
        />
        <QuickStatCard
          icon={CpuChipIcon}
          label="GPU Status"
          value={gpuAvailable ? 'Ready' : 'N/A'}
          loading={modelLoading}
          href="/settings"
          valueColor={gpuAvailable ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Jobs */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-secondary-100">
              Recent Jobs
            </h2>
            <Link to="/jobs" className="text-sm text-primary-400 hover:text-primary-300">
              View All →
            </Link>
          </div>
          {jobsLoading ? (
            <LoadingSpinner className="mx-auto" />
          ) : allJobs.length > 0 ? (
            <div className="space-y-3">
              {allJobs.slice(0, 5).map((job) => (
                <Link
                  key={job.id}
                  to={`/jobs/${job.id}`}
                  className="flex items-center justify-between p-3 bg-secondary-800/50 rounded-lg hover:bg-secondary-700/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <JobStatusIcon status={job.status} />
                    <div>
                      <p className="text-sm font-medium text-secondary-200">
                        {job.name || `Job ${job.id.slice(0, 8)}`}
                      </p>
                      <p className="text-xs text-secondary-400">
                        {job.current_stage || 'Pending'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-secondary-400">
                      {job.progress ?? 0}%
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-secondary-400">
              <ClockIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No jobs yet</p>
              <Link
                to="/datasets"
                className="text-primary-400 hover:text-primary-300 text-sm mt-2 inline-block"
              >
                Create your first dataset →
              </Link>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-secondary-100 mb-4">
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <QuickActionButton
              icon={FolderPlusIcon}
              label="New Dataset"
              description="Import SVO2 files"
              href="/datasets"
            />
            <QuickActionButton
              icon={PlayIcon}
              label="New Job"
              description="Start processing"
              href="/jobs"
            />
            <QuickActionButton
              icon={TagIcon}
              label="Browse Data"
              description="View extracted frames"
              href="/data"
            />
            <QuickActionButton
              icon={ArrowDownTrayIcon}
              label="Export Data"
              description="Download training set"
              href="/data"
            />
          </div>
        </div>
      </div>

      {/* Workflow Guide */}
      <div className="card p-6 bg-secondary-800/50 border-secondary-700">
        <h2 className="text-lg font-semibold text-secondary-100 mb-4">
          How It Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <WorkflowGuideStep
            step={1}
            title="Import & Extract"
            description="Create a dataset from SVO2 files. The system extracts RGB frames, depth maps, and sensor data (IMU, magnetometer, barometer)."
          />
          <WorkflowGuideStep
            step={2}
            title="Detect & Track"
            description="Run SAM3 segmentation to detect objects, then track them across frames to maintain consistent IDs throughout the video."
          />
          <WorkflowGuideStep
            step={3}
            title="Review & Export"
            description="Review annotations, import external labels if needed, then export in KITTI format with full data lineage."
          />
        </div>
      </div>
    </div>
  );
}

// Helper Components

function QuickStatCard({
  icon: Icon,
  label,
  value,
  loading,
  href,
  highlight,
  valueColor,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  loading?: boolean;
  href: string;
  highlight?: boolean;
  valueColor?: string;
}) {
  return (
    <Link
      to={href}
      className={`card p-4 hover:bg-secondary-700/50 transition-colors ${
        highlight ? 'border-primary-500/50' : ''
      }`}
    >
      <div className="flex items-center gap-3">
        <Icon
          className={`w-8 h-8 ${highlight ? 'text-primary-400' : 'text-secondary-400'}`}
        />
        <div>
          {loading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <p className={`text-2xl font-bold ${valueColor || 'text-secondary-100'}`}>
              {value}
            </p>
          )}
          <p className="text-xs text-secondary-400">{label}</p>
        </div>
      </div>
    </Link>
  );
}

function QuickActionButton({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="flex items-center gap-3 p-3 bg-secondary-800/50 rounded-lg hover:bg-secondary-700/50 transition-colors group"
    >
      <Icon className="w-8 h-8 text-primary-400 group-hover:text-primary-300" />
      <div>
        <p className="text-sm font-medium text-secondary-200">{label}</p>
        <p className="text-xs text-secondary-400">{description}</p>
      </div>
    </Link>
  );
}

function WorkflowGuideStep({
  step,
  title,
  description,
}: {
  step: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-600/30 border border-primary-500 flex items-center justify-center">
        <span className="text-lg font-bold text-primary-400">{step}</span>
      </div>
      <div>
        <h3 className="font-semibold text-secondary-200 mb-1">{title}</h3>
        <p className="text-sm text-secondary-400">{description}</p>
      </div>
    </div>
  );
}

function JobStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircleIcon className="w-5 h-5 text-green-400" />;
    case 'running':
      return <PlayIcon className="w-5 h-5 text-primary-400" />;
    case 'failed':
      return <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />;
    default:
      return <ClockIcon className="w-5 h-5 text-secondary-400" />;
  }
}
