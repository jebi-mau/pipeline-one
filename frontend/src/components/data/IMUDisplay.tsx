/**
 * Shalom - IMU Data Display with horizontal bar graphs
 */

import type { FrameMetadataSummary } from '../../types/data';

interface IMUDisplayProps {
  metadata: FrameMetadataSummary;
}

interface BarGraphProps {
  label: string;
  value: number | null;
  min: number;
  max: number;
  unit: string;
  color: string;
}

function BarGraph({ label, value, min, max, unit, color }: BarGraphProps) {
  if (value === null || value === undefined) {
    return (
      <div className="flex items-center space-x-2 h-6">
        <span className="w-6 text-xs text-secondary-400 font-medium">{label}</span>
        <div className="flex-1 h-3 bg-secondary-700 rounded-full">
          <div className="h-full bg-secondary-600 rounded-full w-0" />
        </div>
        <span className="w-20 text-xs text-secondary-500 text-right">N/A</span>
      </div>
    );
  }

  // Calculate bar position and width
  const range = max - min;
  const center = (0 - min) / range; // Position of zero on the scale
  const normalized = (value - min) / range;

  // For values around zero, show bar from center
  const isPositive = value >= 0;
  const barStart = isPositive ? center : normalized;
  const barWidth = isPositive ? normalized - center : center - normalized;

  return (
    <div className="flex items-center space-x-2 h-6">
      <span className="w-6 text-xs text-secondary-400 font-medium">{label}</span>
      <div className="flex-1 h-3 bg-secondary-700 rounded-full relative overflow-hidden">
        {/* Center line (zero) */}
        <div
          className="absolute top-0 bottom-0 w-px bg-secondary-500"
          style={{ left: `${center * 100}%` }}
        />
        {/* Value bar */}
        <div
          className="absolute top-0 bottom-0 rounded-full"
          style={{
            left: `${barStart * 100}%`,
            width: `${Math.max(barWidth * 100, 1)}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span className="w-20 text-xs text-secondary-300 text-right font-mono">
        {value.toFixed(2)} {unit}
      </span>
    </div>
  );
}

interface OrientationDisplayProps {
  roll: number | null;
  pitch: number | null;
  yaw: number | null;
}

function OrientationDisplay({ roll, pitch, yaw }: OrientationDisplayProps) {
  const formatAngle = (angle: number | null) => {
    if (angle === null || angle === undefined) return 'N/A';
    return `${angle >= 0 ? '+' : ''}${angle.toFixed(1)}`;
  };

  return (
    <div className="flex items-center space-x-4 text-xs">
      <div className="flex items-center space-x-1">
        <span className="text-secondary-400">Roll:</span>
        <span className="text-secondary-200 font-mono">{formatAngle(roll)}</span>
      </div>
      <div className="flex items-center space-x-1">
        <span className="text-secondary-400">Pitch:</span>
        <span className="text-secondary-200 font-mono">{formatAngle(pitch)}</span>
      </div>
      <div className="flex items-center space-x-1">
        <span className="text-secondary-400">Yaw:</span>
        <span className="text-secondary-200 font-mono">{formatAngle(yaw)}</span>
      </div>
    </div>
  );
}

export function IMUDisplay({ metadata }: IMUDisplayProps) {
  return (
    <div className="space-y-3">
      {/* Accelerometer Section */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-secondary-300">Accelerometer</span>
          <span className="text-xs text-secondary-500">m/s2</span>
        </div>
        <div className="space-y-1">
          <BarGraph
            label="X"
            value={metadata.accel_x}
            min={-20}
            max={20}
            unit=""
            color="#ef4444" // red
          />
          <BarGraph
            label="Y"
            value={metadata.accel_y}
            min={-20}
            max={20}
            unit=""
            color="#22c55e" // green
          />
          <BarGraph
            label="Z"
            value={metadata.accel_z}
            min={-20}
            max={20}
            unit=""
            color="#3b82f6" // blue
          />
        </div>
      </div>

      {/* Gyroscope Section */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-secondary-300">Gyroscope</span>
          <span className="text-xs text-secondary-500">rad/s</span>
        </div>
        <div className="space-y-1">
          <BarGraph
            label="X"
            value={metadata.gyro_x}
            min={-5}
            max={5}
            unit=""
            color="#ef4444" // red
          />
          <BarGraph
            label="Y"
            value={metadata.gyro_y}
            min={-5}
            max={5}
            unit=""
            color="#22c55e" // green
          />
          <BarGraph
            label="Z"
            value={metadata.gyro_z}
            min={-5}
            max={5}
            unit=""
            color="#3b82f6" // blue
          />
        </div>
      </div>

      {/* Orientation Section */}
      {(metadata.orientation_roll !== null ||
        metadata.orientation_pitch !== null ||
        metadata.orientation_yaw !== null) && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-secondary-300">Orientation</span>
            <span className="text-xs text-secondary-500">degrees</span>
          </div>
          <OrientationDisplay
            roll={metadata.orientation_roll}
            pitch={metadata.orientation_pitch}
            yaw={metadata.orientation_yaw}
          />
        </div>
      )}
    </div>
  );
}
