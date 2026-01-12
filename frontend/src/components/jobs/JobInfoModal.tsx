/**
 * Shalom - Job Info Modal component
 * Shows details about files being processed and job settings
 */

import { Modal } from '../common/Modal';
import {
  DocumentIcon,
  Cog6ToothIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  BeakerIcon,
} from '@heroicons/react/24/outline';
import type { Job } from '../../types/job';
import { StageProgressBar } from './StageProgressBar';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';

interface JobInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: Job | null;
}

export function JobInfoModal({ isOpen, onClose, job }: JobInfoModalProps) {
  if (!job) return null;

  const inputFiles = job.input_paths || job.input_files || [];
  const config = job.config || {};

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Job Details: ${job.name}`} size="lg">
      <div className="space-y-6">
        {/* Pipeline Progress */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <BeakerIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Pipeline Progress</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4">
            <StageProgressBar
              stages={job.stages_to_run || ALL_PIPELINE_STAGES}
              currentStage={job.current_stage || 0}
              currentStageName={job.current_stage_name}
              progress={job.progress || 0}
              processedFrames={job.processed_frames}
              totalFrames={job.total_frames}
              jobStatus={job.status}
            />
          </div>
          {job.stages_to_run && job.stages_to_run.length < ALL_PIPELINE_STAGES.length && (
            <div className="mt-2 text-xs text-secondary-500">
              Selected stages: {job.stages_to_run.map(s => STAGE_INFO[s]?.name || s).join(' → ')}
            </div>
          )}
        </div>

        {/* Input Files */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <DocumentIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Input Files ({inputFiles.length})</h3>
          </div>
          {inputFiles.length > 0 ? (
            <div className="bg-secondary-800 rounded-lg divide-y divide-secondary-700 max-h-40 overflow-y-auto">
              {inputFiles.map((file, idx) => (
                <div key={idx} className="px-3 py-2 text-sm">
                  <div className="text-secondary-300 truncate" title={file}>
                    {file.split('/').pop()}
                  </div>
                  <div className="text-xs text-secondary-500 truncate" title={file}>
                    {file}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-secondary-800 rounded-lg p-3 text-sm text-secondary-500">
              No input files specified
            </div>
          )}
        </div>

        {/* Object Classes */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircleIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Object Classes</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {(config.object_class_ids || job.object_classes || []).map((cls, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-primary-900/50 text-primary-300 rounded text-xs"
              >
                {cls}
              </span>
            ))}
            {(config.object_class_ids || job.object_classes || []).length === 0 && (
              <span className="text-sm text-secondary-500">No object classes specified</span>
            )}
          </div>
        </div>

        {/* Processing Settings */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <Cog6ToothIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Processing Settings</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-secondary-500">Model Variant:</span>
                <span className="ml-2 text-secondary-300">
                  {config.sam3_model_variant || 'sam3_hiera_large'}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">Confidence:</span>
                <span className="ml-2 text-secondary-300">
                  {config.sam3_confidence_threshold ?? config.sam3_confidence ?? 0.5}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">Batch Size:</span>
                <span className="ml-2 text-secondary-300">
                  {config.sam3_batch_size ?? config.batch_size ?? 4}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">Frame Skip:</span>
                <span className="ml-2 text-secondary-300">
                  {config.frame_skip ?? 1}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">IOU Threshold:</span>
                <span className="ml-2 text-secondary-300">
                  {config.sam3_iou_threshold ?? 0.7}
                </span>
              </div>
              <div>
                <span className="text-secondary-500">Tracking:</span>
                <span className="ml-2 text-secondary-300">
                  {config.enable_tracking ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Timestamps */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <ClockIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Timeline</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-secondary-500">Created:</span>
              <span className="text-secondary-300">
                {new Date(job.created_at).toLocaleString()}
              </span>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <span className="text-secondary-500">Started:</span>
                <span className="text-secondary-300">
                  {new Date(job.started_at).toLocaleString()}
                </span>
              </div>
            )}
            {job.completed_at && (
              <div className="flex justify-between">
                <span className="text-secondary-500">Completed:</span>
                <span className="text-secondary-300">
                  {new Date(job.completed_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {job.error_message && (
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <XCircleIcon className="w-5 h-5 text-red-400" />
              <h3 className="text-sm font-medium text-red-400">Error</h3>
            </div>
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 text-sm text-red-300">
              {job.error_message}
            </div>
          </div>
        )}

        {/* Close Button */}
        <div className="flex justify-end pt-4 border-t border-secondary-700">
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
