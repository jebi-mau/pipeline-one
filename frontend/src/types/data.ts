/**
 * Shalom - Data type definitions for frame browsing and correlation
 */

export interface BBox2D {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BBox3D {
  x: number;
  y: number;
  z: number;
  length: number;
  width: number;
  height: number;
  rotation_y: number;
}

export interface AnnotationSummary {
  id: string;
  class_name: string;
  class_color: string;
  confidence: number;
  bbox_2d: BBox2D;
  bbox_3d: BBox3D | null;
  mask_url: string | null;
  track_id: string | null;
}

export interface FrameMetadataSummary {
  image_width: number | null;
  image_height: number | null;
  // Accelerometer (m/s²)
  accel_x: number | null;
  accel_y: number | null;
  accel_z: number | null;
  // Gyroscope (rad/s)
  gyro_x: number | null;
  gyro_y: number | null;
  gyro_z: number | null;
  // Orientation (degrees)
  orientation_roll: number | null;
  orientation_pitch: number | null;
  orientation_yaw: number | null;
}

export interface FrameSummary {
  id: string;
  frame_id: string;
  sequence_index: number;
  svo2_frame_index: number;
  svo2_file: string;
  timestamp_ns: number | null;
  has_left_image: boolean;
  has_right_image: boolean;
  has_depth: boolean;
  has_pointcloud: boolean;
  detection_count: number;
  thumbnail_url: string | null;
}

export interface FrameDetail {
  id: string;
  frame_id: string;
  sequence_index: number;
  svo2_frame_index: number;
  svo2_file: string;
  timestamp_ns: number | null;
  image_left_url: string | null;
  image_right_url: string | null;
  depth_url: string | null;
  pointcloud_url: string | null;
  segmentation_complete: boolean;
  reconstruction_complete: boolean;
  tracking_complete: boolean;
  annotations: AnnotationSummary[];
  metadata: FrameMetadataSummary | null;
}

export interface FrameListResponse {
  frames: FrameSummary[];
  total: number;
  limit: number;
  offset: number;
  job_id: string;
}

export interface SVO2FileSummary {
  filename: string;
  path: string;
  total_frames_original: number | null;
  frames_extracted: number;
  frame_skip: number;
}

export interface DataSummary {
  job_id: string;
  job_name: string;
  status: string;
  total_frames: number;
  frames_with_left_image: number;
  frames_with_right_image: number;
  frames_with_depth: number;
  frames_with_pointcloud: number;
  total_detections: number;
  detections_by_class: Record<string, number>;
  total_tracks: number;
  svo2_files: SVO2FileSummary[];
  output_directory: string | null;
  frame_skip: number;
  created_at: string | null;
  completed_at: string | null;
}

export interface CorrelationEntry {
  sequence_index: number;
  svo2_frame_index: number;
  frame_id: string;
  has_left_image: boolean;
  has_right_image: boolean;
  has_depth: boolean;
  has_pointcloud: boolean;
  has_imu: boolean;
  detection_count: number;
}

export interface CorrelationTableResponse {
  entries: CorrelationEntry[];
  total: number;
  svo2_file: string;
  frame_skip: number;
}
