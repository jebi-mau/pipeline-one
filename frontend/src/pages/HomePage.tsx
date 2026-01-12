/**
 * Shalom - Home page with real-time system status
 */

import { Link } from 'react-router-dom';
import {
  FolderOpenIcon,
  CpuChipIcon,
  DocumentArrowDownIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { useJobs } from '../hooks/useJobs';
import { useModelInfo, useSystemConfig } from '../hooks/useConfig';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

const features = [
  {
    name: 'SVO2 File Browser',
    description: 'Browse and select SVO2 files from your local filesystem',
    icon: FolderOpenIcon,
  },
  {
    name: 'SAM 3 Detection',
    description: 'Run text-prompt object detection using SAM 3 locally on RTX 5090',
    icon: CpuChipIcon,
  },
  {
    name: 'KITTI Export',
    description: 'Export detections in KITTI format with full traceability',
    icon: DocumentArrowDownIcon,
  },
  {
    name: '3D Visualization',
    description: 'View point clouds and 3D bounding boxes in the browser',
    icon: ChartBarIcon,
  },
];

export default function HomePage() {
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ status: 'running' });
  const { data: modelInfo, isLoading: modelLoading } = useModelInfo();
  const { data: systemConfig } = useSystemConfig();

  const activeJobsCount = jobsData?.jobs?.length ?? 0;
  const gpuAvailable = modelInfo?.gpu_available ?? false;
  const vramGb = modelInfo?.gpu_vram_gb ?? 0;
  const loadedModel = modelInfo?.loaded_model ?? 'None';

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-secondary-100 mb-4">
          Shalom - SVO2-SAM3 Analyzer
        </h1>
        <p className="text-lg text-secondary-400 max-w-2xl mx-auto">
          Process Stereolabs ZED 2i camera recordings with SAM 3 object detection.
          100% local processing on your RTX 5090.
        </p>
        <div className="mt-8">
          <Link to="/jobs" className="btn-primary">
            Create New Job
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {features.map((feature) => (
          <div key={feature.name} className="card p-6">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0">
                <feature.icon className="w-8 h-8 text-primary-500" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-secondary-100">
                  {feature.name}
                </h3>
                <p className="mt-1 text-sm text-secondary-400">
                  {feature.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* System Status */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">System Status</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            {jobsLoading ? (
              <LoadingSpinner size="sm" className="mx-auto mb-2" />
            ) : (
              <p className="text-3xl font-bold text-primary-500">{activeJobsCount}</p>
            )}
            <p className="text-sm text-secondary-400">Active Jobs</p>
          </div>
          <div className="text-center">
            {modelLoading ? (
              <LoadingSpinner size="sm" className="mx-auto mb-2" />
            ) : (
              <p className={`text-3xl font-bold ${gpuAvailable ? 'text-green-500' : 'text-red-500'}`}>
                {gpuAvailable ? 'Ready' : 'N/A'}
              </p>
            )}
            <p className="text-sm text-secondary-400">GPU Status</p>
          </div>
          <div className="text-center">
            {modelLoading ? (
              <LoadingSpinner size="sm" className="mx-auto mb-2" />
            ) : (
              <p className="text-3xl font-bold text-secondary-100">
                {vramGb > 0 ? `${vramGb} GB` : 'N/A'}
              </p>
            )}
            <p className="text-sm text-secondary-400">VRAM Available</p>
          </div>
          <div className="text-center">
            {modelLoading ? (
              <LoadingSpinner size="sm" className="mx-auto mb-2" />
            ) : (
              <p className="text-3xl font-bold text-secondary-100 truncate">
                {loadedModel || 'None'}
              </p>
            )}
            <p className="text-sm text-secondary-400">Model Loaded</p>
          </div>
        </div>
      </div>

      {/* Recent Jobs Quick Stats */}
      {systemConfig && (
        <div className="card p-6">
          <h2 className="text-lg font-medium text-secondary-100 mb-4">Configuration</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-secondary-400">SVO2 Directory:</span>
              <span className="ml-2 text-secondary-100 block truncate">
                {systemConfig.svo2_directory}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">Output Directory:</span>
              <span className="ml-2 text-secondary-100 block truncate">
                {systemConfig.output_directory}
              </span>
            </div>
            <div>
              <span className="text-secondary-400">Processing Workers:</span>
              <span className="ml-2 text-secondary-100">
                {systemConfig.max_workers}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
