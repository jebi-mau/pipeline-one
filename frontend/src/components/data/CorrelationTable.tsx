/**
 * Pipeline One - Correlation Table component showing data availability per frame
 */

import { useState } from 'react';
import { CheckIcon, XMarkIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { useCorrelationTable } from '../../hooks/useData';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';

interface CorrelationTableProps {
  jobId: string;
}

export function CorrelationTable({ jobId }: CorrelationTableProps) {
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const { data, isLoading, error } = useCorrelationTable(jobId, {
    limit: pageSize,
    offset: page * pageSize,
  });

  if (isLoading) {
    return (
      <div className="card p-12 flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage title="Failed to load correlation data" message="Could not fetch frame correlation data" />;
  }

  if (!data || data.entries.length === 0) {
    return (
      <div className="card p-12 text-center">
        <p className="text-secondary-400">No correlation data available.</p>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  const StatusCell = ({ value }: { value: boolean }) => (
    <td className="px-4 py-2 text-center">
      {value ? (
        <CheckIcon className="w-4 h-4 text-green-400 mx-auto" />
      ) : (
        <XMarkIcon className="w-4 h-4 text-secondary-600 mx-auto" />
      )}
    </td>
  );

  return (
    <div className="space-y-4">
      {/* Table Info */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-secondary-400">
          <span className="font-medium text-secondary-200">{data.svo2_file}</span>
          <span className="ml-2">(Frame Skip: {data.frame_skip})</span>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs text-secondary-400">
            <span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> RGB Left
            <span className="w-3 h-3 rounded-full bg-blue-500 inline-block ml-2" /> RGB Right
            <span className="w-3 h-3 rounded-full bg-purple-500 inline-block ml-2" /> Depth
            <span className="w-3 h-3 rounded-full bg-orange-500 inline-block ml-2" /> Point Cloud
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-secondary-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase">
                  Seq #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase">
                  SVO2 Frame
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-secondary-300 uppercase">
                  Frame ID
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-secondary-300 uppercase">
                  Left
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-secondary-300 uppercase">
                  Right
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-secondary-300 uppercase">
                  Depth
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-secondary-300 uppercase">
                  PC
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-secondary-300 uppercase">
                  IMU
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-secondary-300 uppercase">
                  Detections
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary-700">
              {data.entries.map((entry) => (
                <tr
                  key={entry.frame_id}
                  className="hover:bg-secondary-700/50 transition-colors"
                >
                  <td className="px-4 py-2 text-sm text-secondary-300">
                    {entry.sequence_index}
                  </td>
                  <td className="px-4 py-2 text-sm text-secondary-300">
                    {entry.svo2_frame_index}
                  </td>
                  <td className="px-4 py-2 text-sm text-secondary-400 font-mono text-xs">
                    {entry.frame_id}
                  </td>
                  <StatusCell value={entry.has_left_image} />
                  <StatusCell value={entry.has_right_image} />
                  <StatusCell value={entry.has_depth} />
                  <StatusCell value={entry.has_pointcloud} />
                  <StatusCell value={entry.has_imu} />
                  <td className="px-4 py-2 text-sm text-secondary-300 text-right">
                    {entry.detection_count > 0 ? (
                      <span className="px-2 py-0.5 bg-primary-600/20 text-primary-400 rounded text-xs">
                        {entry.detection_count}
                      </span>
                    ) : (
                      <span className="text-secondary-600">0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-secondary-400">
            Showing {page * pageSize + 1} -{' '}
            {Math.min((page + 1) * pageSize, data.total)} of {data.total} entries
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
  );
}
