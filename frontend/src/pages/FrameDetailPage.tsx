/**
 * Frame Detail Page
 * Displays comprehensive frame information including:
 * - Frame images (left/right/depth)
 * - Source SVO2 file info
 * - Original Unix timestamp
 * - Camera serial number
 * - IMU/sensor data
 * - Annotations on this frame
 * - Download links for NumPy arrays
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LoadingSpinner, ErrorMessage } from '../components/common';
import { LineageBreadcrumb, buildBreadcrumbFromFrameLineage } from '../components/common/LineageBreadcrumb';
import { getFrameLineage } from '../services/lineageService';
import type { FrameLineage } from '../types/lineage';

export default function FrameDetailPage() {
  const { frameId } = useParams<{ frameId: string }>();
  const [lineage, setLineage] = useState<FrameLineage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeImageTab, setActiveImageTab] = useState<'left' | 'right' | 'depth'>('left');

  useEffect(() => {
    if (!frameId) return;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getFrameLineage(frameId!);
        setLineage(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load frame data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [frameId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !lineage) {
    return (
      <div className="p-6">
        <ErrorMessage message={error || 'Frame not found'} />
      </div>
    );
  }

  const { frame, dataset_file, dataset, job, annotations, sensor_data } = lineage;
  const breadcrumbs = buildBreadcrumbFromFrameLineage(lineage);

  // Format timestamp
  const unixTimestamp = frame.original_unix_timestamp
    ? new Date(frame.original_unix_timestamp * 1000).toLocaleString()
    : 'N/A';

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb Navigation */}
      <LineageBreadcrumb segments={breadcrumbs} className="mb-4" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Frame {frame.sequence_index}
          </h1>
          <p className="text-gray-400 mt-1">
            SVO2 Frame Index: {frame.svo2_frame_index}
          </p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm ${
            frame.extraction_status === 'completed'
              ? 'bg-green-500/20 text-green-400'
              : frame.extraction_status === 'failed'
              ? 'bg-red-500/20 text-red-400'
              : 'bg-yellow-500/20 text-yellow-400'
          }`}
        >
          {frame.extraction_status}
        </span>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Image Viewer */}
        <div className="lg:col-span-2 bg-gray-800 rounded-lg overflow-hidden">
          {/* Image Tabs */}
          <div className="flex border-b border-gray-700">
            {['left', 'right', 'depth'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveImageTab(tab as 'left' | 'right' | 'depth')}
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  activeImageTab === tab
                    ? 'text-primary-400 border-b-2 border-primary-400 bg-gray-700/50'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)} Image
              </button>
            ))}
          </div>

          {/* Image Display */}
          <div className="aspect-video bg-gray-900 flex items-center justify-center">
            {activeImageTab === 'left' && frame.image_left_path ? (
              <img
                src={`/api/data/files/${job?.id}/${frame.image_left_path}`}
                alt="Left camera view"
                className="max-w-full max-h-full object-contain"
              />
            ) : activeImageTab === 'right' && frame.image_right_path ? (
              <img
                src={`/api/data/files/${job?.id}/${frame.image_right_path}`}
                alt="Right camera view"
                className="max-w-full max-h-full object-contain"
              />
            ) : activeImageTab === 'depth' && frame.depth_path ? (
              <img
                src={`/api/data/files/${job?.id}/${frame.depth_path}`}
                alt="Depth map"
                className="max-w-full max-h-full object-contain"
              />
            ) : (
              <p className="text-gray-500">No image available</p>
            )}
          </div>

          {/* Download Links */}
          {frame.numpy_path && (
            <div className="p-4 bg-gray-700/50 border-t border-gray-700">
              <a
                href={`/api/data/files/${job?.id}/${frame.numpy_path}`}
                download
                className="inline-flex items-center gap-2 text-primary-400 hover:text-primary-300 text-sm"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download NumPy Array
              </a>
            </div>
          )}
        </div>

        {/* Info Sidebar */}
        <div className="space-y-4">
          {/* Source Info */}
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-3">Source Info</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-400">SVO2 File</dt>
                <dd className="text-white">{frame.original_svo2_filename || 'N/A'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-400">Unix Timestamp</dt>
                <dd className="text-white">{unixTimestamp}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-400">Timestamp (ns)</dt>
                <dd className="text-white font-mono text-xs">{frame.timestamp_ns}</dd>
              </div>
              {dataset_file && (
                <>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Camera Serial</dt>
                    <dd className="text-white">{dataset_file.camera_serial || 'N/A'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Camera Model</dt>
                    <dd className="text-white">{dataset_file.camera_model || 'N/A'}</dd>
                  </div>
                </>
              )}
            </dl>
          </div>

          {/* Dataset Info */}
          {dataset && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Dataset</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-400">Name</dt>
                  <dd>
                    <Link
                      to={`/datasets/${dataset.id}`}
                      className="text-primary-400 hover:text-primary-300"
                    >
                      {dataset.name}
                    </Link>
                  </dd>
                </div>
                {dataset.customer && (
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Customer</dt>
                    <dd className="text-white">{dataset.customer}</dd>
                  </div>
                )}
                {dataset.site && (
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Site</dt>
                    <dd className="text-white">{dataset.site}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {/* Job Info */}
          {job && (
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Processing Job</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-400">Job</dt>
                  <dd>
                    <Link
                      to={`/jobs/${job.id}`}
                      className="text-primary-400 hover:text-primary-300"
                    >
                      {job.name}
                    </Link>
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-400">Status</dt>
                  <dd className="text-white">{job.status}</dd>
                </div>
                {job.depth_mode && (
                  <div className="flex justify-between">
                    <dt className="text-gray-400">Depth Mode</dt>
                    <dd className="text-white">{job.depth_mode}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      </div>

      {/* Sensor Data Section */}
      {sensor_data && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Sensor Data</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* IMU Accelerometer */}
            <div className="bg-gray-700/50 rounded p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Accelerometer (m/s²)</h4>
              <div className="space-y-1 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-red-400">X:</span>
                  <span className="text-white">{sensor_data.imu.accel.x?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-green-400">Y:</span>
                  <span className="text-white">{sensor_data.imu.accel.y?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-400">Z:</span>
                  <span className="text-white">{sensor_data.imu.accel.z?.toFixed(4) ?? 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* IMU Gyroscope */}
            <div className="bg-gray-700/50 rounded p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Gyroscope (rad/s)</h4>
              <div className="space-y-1 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-red-400">X:</span>
                  <span className="text-white">{sensor_data.imu.gyro.x?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-green-400">Y:</span>
                  <span className="text-white">{sensor_data.imu.gyro.y?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-400">Z:</span>
                  <span className="text-white">{sensor_data.imu.gyro.z?.toFixed(4) ?? 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* Magnetometer */}
            {sensor_data.magnetometer && (
              <div className="bg-gray-700/50 rounded p-4">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Magnetometer (µT)</h4>
                <div className="space-y-1 font-mono text-sm">
                  <div className="flex justify-between">
                    <span className="text-red-400">X:</span>
                    <span className="text-white">{sensor_data.magnetometer.x?.toFixed(2) ?? 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-400">Y:</span>
                    <span className="text-white">{sensor_data.magnetometer.y?.toFixed(2) ?? 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-400">Z:</span>
                    <span className="text-white">{sensor_data.magnetometer.z?.toFixed(2) ?? 'N/A'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Barometer */}
            {sensor_data.barometer && (
              <div className="bg-gray-700/50 rounded p-4">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Barometer</h4>
                <div className="space-y-1 font-mono text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Pressure:</span>
                    <span className="text-white">{sensor_data.barometer.pressure_hpa?.toFixed(2) ?? 'N/A'} hPa</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Altitude:</span>
                    <span className="text-white">{sensor_data.barometer.altitude_m?.toFixed(2) ?? 'N/A'} m</span>
                  </div>
                </div>
              </div>
            )}

            {/* Temperature */}
            {(sensor_data.temperature.imu_c || sensor_data.temperature.barometer_c) && (
              <div className="bg-gray-700/50 rounded p-4">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Temperature</h4>
                <div className="space-y-1 font-mono text-sm">
                  {sensor_data.temperature.imu_c && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">IMU:</span>
                      <span className="text-white">{sensor_data.temperature.imu_c.toFixed(1)}°C</span>
                    </div>
                  )}
                  {sensor_data.temperature.barometer_c && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Barometer:</span>
                      <span className="text-white">{sensor_data.temperature.barometer_c.toFixed(1)}°C</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Orientation */}
            <div className="bg-gray-700/50 rounded p-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Orientation (Quat)</h4>
              <div className="space-y-1 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-purple-400">W:</span>
                  <span className="text-white">{sensor_data.imu.orientation.w?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-red-400">X:</span>
                  <span className="text-white">{sensor_data.imu.orientation.x?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-green-400">Y:</span>
                  <span className="text-white">{sensor_data.imu.orientation.y?.toFixed(4) ?? 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-400">Z:</span>
                  <span className="text-white">{sensor_data.imu.orientation.z?.toFixed(4) ?? 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Annotations Section */}
      {annotations.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            Annotations ({annotations.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 pr-4">Label</th>
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 pr-4">Bounding Box</th>
                  <th className="pb-3 pr-4">Match Strategy</th>
                  <th className="pb-3">Source Image</th>
                </tr>
              </thead>
              <tbody>
                {annotations.map((ann) => (
                  <tr key={ann.id} className="border-b border-gray-700/50 text-sm">
                    <td className="py-3 pr-4">
                      <span className="inline-flex items-center px-2 py-1 rounded bg-primary-500/20 text-primary-400">
                        {ann.label}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-300">{ann.annotation_type}</td>
                    <td className="py-3 pr-4 text-gray-300 font-mono text-xs">
                      {ann.bbox
                        ? `[${ann.bbox.map((n) => n.toFixed(0)).join(', ')}]`
                        : 'N/A'}
                    </td>
                    <td className="py-3 pr-4 text-gray-300">{ann.match_strategy || 'N/A'}</td>
                    <td className="py-3 text-gray-400 truncate max-w-[200px]">
                      {ann.source_image_name}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
