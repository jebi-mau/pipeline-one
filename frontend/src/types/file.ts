/**
 * Shalom - File browser type definitions
 */

export interface DirectoryInfo {
  name: string;
  path: string;
  item_count: number;
}

export interface FileInfo {
  name: string;
  path: string;
  size_bytes: number;
  size: number;
  modified_at: number;
  metadata?: Record<string, unknown> | null;
}

export interface DirectoryContents {
  path: string;
  directories: DirectoryInfo[];
  files: FileInfo[];
}

export interface FileMetadata {
  path: string;
  name: string;
  size_bytes: number;
  duration_ms: number;
  frame_count: number;
  fps: number;
  resolution: [number, number];
  depth_mode: string;
  has_imu: boolean;
  serial_number: string;
  firmware_version: string;
  created_at: number;
}
