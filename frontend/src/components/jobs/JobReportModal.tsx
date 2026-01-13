/**
 * Pipeline One - Job Report Modal component
 * Displays comprehensive job report with all details and PDF download
 */

import { useState } from 'react';
import { Modal } from '../common/Modal';
import {
  DocumentIcon,
  Cog6ToothIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  BeakerIcon,
  ChartBarIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import type { Job } from '../../types/job';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';
import { useJobResults } from '../../hooks/useJobs';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { JobReportPDF } from './JobReportPDF';
import { pdf } from '@react-pdf/renderer';

interface JobReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: Job | null;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  paused: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  completed: 'bg-green-500/20 text-green-400 border-green-500/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  cancelled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) return `${mins}m ${secs.toFixed(0)}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString();
}

function calculateProcessingTime(job: Job): number | null {
  if (!job.started_at) return null;
  const start = new Date(job.started_at);
  const end = job.completed_at ? new Date(job.completed_at) : new Date();
  return (end.getTime() - start.getTime()) / 1000;
}

export function JobReportModal({ isOpen, onClose, job }: JobReportModalProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { data: results } = useJobResults(
    job?.status === 'completed' ? job?.id : undefined
  );

  if (!job) return null;

  const inputFiles = job.input_paths || job.input_files || [];
  const config = job.config || {};
  const processingTime = calculateProcessingTime(job);
  const stages = job.stages_to_run || ALL_PIPELINE_STAGES;

  const handleDownloadPDF = async () => {
    setIsDownloading(true);
    let url: string | null = null;

    try {
      const blob = await pdf(
        <JobReportPDF job={job} results={results || undefined} />
      ).toBlob();

      url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `job-report-${job.name.replace(/\s+/g, '-').toLowerCase()}-${job.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to generate PDF:', error);
    } finally {
      // Always cleanup URL object to prevent memory leak
      if (url) {
        URL.revokeObjectURL(url);
      }
      setIsDownloading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Job Report" size="xl">
      <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
        {/* Header with Job Name and Status */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold text-secondary-100">{job.name}</h2>
            <p className="text-sm text-secondary-500 mt-1">ID: {job.id}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium border ${statusColors[job.status]}`}>
            {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
          </span>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-secondary-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-primary-400">
              {job.total_frames || 0}
            </div>
            <div className="text-xs text-secondary-500 mt-1">Total Frames</div>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {job.processed_frames || 0}
            </div>
            <div className="text-xs text-secondary-500 mt-1">Processed</div>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">
              {results?.statistics?.total_detections || 0}
            </div>
            <div className="text-xs text-secondary-500 mt-1">Detections</div>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-400">
              {results?.statistics?.total_tracks || 0}
            </div>
            <div className="text-xs text-secondary-500 mt-1">Tracks</div>
          </div>
        </div>

        {/* Pipeline Stages */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <BeakerIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Pipeline Stages</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              {ALL_PIPELINE_STAGES.map((stage, idx) => {
                const isSelected = stages.includes(stage);
                const stageNum = STAGE_INFO[stage].number;
                const isCompleted = job.current_stage ? job.current_stage >= stageNum : false;
                const isCurrent = job.current_stage === stageNum;

                return (
                  <div key={stage} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                          !isSelected
                            ? 'bg-secondary-700 text-secondary-500'
                            : isCompleted
                            ? 'bg-green-600 text-white'
                            : isCurrent
                            ? 'bg-blue-600 text-white animate-pulse'
                            : 'bg-secondary-700 text-secondary-400'
                        }`}
                      >
                        {stageNum}
                      </div>
                      <span className={`text-xs mt-2 ${isSelected ? 'text-secondary-300' : 'text-secondary-600'}`}>
                        {STAGE_INFO[stage].name}
                      </span>
                    </div>
                    {idx < ALL_PIPELINE_STAGES.length - 1 && (
                      <div className={`w-12 h-0.5 mx-2 ${
                        isSelected && stages.includes(ALL_PIPELINE_STAGES[idx + 1])
                          ? isCompleted ? 'bg-green-600' : 'bg-secondary-600'
                          : 'bg-secondary-700'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
            {job.progress !== undefined && job.progress > 0 && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-secondary-400 mb-1">
                  <span>Overall Progress</span>
                  <span>{job.progress.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-secondary-700 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input Files */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <DocumentIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Input Files ({inputFiles.length})</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg divide-y divide-secondary-700">
            {inputFiles.map((file, idx) => (
              <div key={idx} className="px-4 py-3">
                <div className="text-sm text-secondary-300 font-medium">
                  {file.split('/').pop()}
                </div>
                <div className="text-xs text-secondary-500 mt-1 font-mono truncate">
                  {file}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Object Classes */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <CheckCircleIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">
              Object Classes ({(config.object_class_ids || []).length})
            </h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4">
            <div className="flex flex-wrap gap-2">
              {(config.object_class_ids || []).map((cls, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1.5 bg-primary-900/50 text-primary-300 rounded-lg text-sm border border-primary-800"
                >
                  {cls}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Detection Results by Class */}
        {results?.statistics?.detections_by_class &&
         Object.keys(results.statistics.detections_by_class).length > 0 && (
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <ChartBarIcon className="w-5 h-5 text-primary-400" />
              <h3 className="text-sm font-medium text-secondary-200">Detections by Class</h3>
            </div>
            <div className="bg-secondary-800 rounded-lg p-4">
              <div className="space-y-3">
                {Object.entries(results.statistics.detections_by_class).map(([cls, count]) => {
                  const total = results.statistics.total_detections || 1;
                  const percentage = (count / total) * 100;
                  return (
                    <div key={cls}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-secondary-300">{cls}</span>
                        <span className="text-secondary-400">{count} ({percentage.toFixed(1)}%)</span>
                      </div>
                      <div className="w-full bg-secondary-700 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Processing Settings */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <Cog6ToothIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Processing Settings</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex justify-between">
                <span className="text-secondary-500">Model Variant</span>
                <span className="text-secondary-300 font-medium">
                  {config.sam3_model_variant || 'sam3_hiera_large'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Confidence Threshold</span>
                <span className="text-secondary-300 font-medium">
                  {config.sam3_confidence_threshold ?? 0.5}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">IOU Threshold</span>
                <span className="text-secondary-300 font-medium">
                  {config.sam3_iou_threshold ?? 0.7}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Batch Size</span>
                <span className="text-secondary-300 font-medium">
                  {config.sam3_batch_size ?? 4}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Frame Skip</span>
                <span className="text-secondary-300 font-medium">
                  {config.frame_skip ?? 1}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Tracking Enabled</span>
                <span className={`font-medium ${config.enable_tracking ? 'text-green-400' : 'text-red-400'}`}>
                  {config.enable_tracking ? 'Yes' : 'No'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">3D Export Enabled</span>
                <span className={`font-medium ${config.export_3d_data ? 'text-green-400' : 'text-red-400'}`}>
                  {config.export_3d_data ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div>
          <div className="flex items-center space-x-2 mb-3">
            <ClockIcon className="w-5 h-5 text-primary-400" />
            <h3 className="text-sm font-medium text-secondary-200">Timeline</h3>
          </div>
          <div className="bg-secondary-800 rounded-lg p-4">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-secondary-500">Created</span>
                <span className="text-secondary-300">{formatDate(job.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Started</span>
                <span className="text-secondary-300">{formatDate(job.started_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary-500">Completed</span>
                <span className="text-secondary-300">{formatDate(job.completed_at)}</span>
              </div>
              {processingTime && (
                <div className="flex justify-between pt-2 border-t border-secondary-700">
                  <span className="text-secondary-500">Processing Time</span>
                  <span className="text-primary-400 font-medium">{formatDuration(processingTime)}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Output Directory */}
        {(job.output_directory || results?.output_directory) && (
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <DocumentTextIcon className="w-5 h-5 text-primary-400" />
              <h3 className="text-sm font-medium text-secondary-200">Output Directory</h3>
            </div>
            <div className="bg-secondary-800 rounded-lg p-4">
              <code className="text-sm text-secondary-300 font-mono">
                {job.output_directory || results?.output_directory}
              </code>
            </div>
          </div>
        )}

        {/* Error Message */}
        {job.error_message && (
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <XCircleIcon className="w-5 h-5 text-red-400" />
              <h3 className="text-sm font-medium text-red-400">Error</h3>
            </div>
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-sm text-red-300">
              {job.error_message}
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="flex justify-between items-center pt-6 mt-6 border-t border-secondary-700">
        <div className="text-xs text-secondary-500">
          Report generated: {new Date().toLocaleString()}
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleDownloadPDF}
            disabled={isDownloading}
            className="btn-primary flex items-center space-x-2"
          >
            {isDownloading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Generating PDF...</span>
              </>
            ) : (
              <>
                <ArrowDownTrayIcon className="w-4 h-4" />
                <span>Download PDF</span>
              </>
            )}
          </button>
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
