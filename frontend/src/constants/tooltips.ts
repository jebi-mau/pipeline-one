/**
 * Pipeline One - Centralized tooltip content
 * Provides consistent help text across the application
 */

// =============================================================================
// Job Configuration Tooltips
// =============================================================================

export const JOB_TOOLTIPS = {
  // Model Selection
  model: {
    title: 'SAM3 Model Selection',
    description: 'Choose the Segment Anything Model variant for detection. Larger models provide better accuracy but require more GPU memory and processing time.',
    variants: {
      tiny: 'Fastest processing, ~4GB VRAM. Best for quick previews or limited GPU memory.',
      small: 'Balanced speed and quality, ~6GB VRAM. Good for most use cases.',
      base: 'Higher quality detections, ~8GB VRAM. Recommended for production data.',
      large: 'Best quality, ~12GB VRAM. Use when accuracy is critical and you have ample GPU resources.',
    },
  },

  // Confidence Threshold
  confidenceThreshold: {
    title: 'Confidence Threshold',
    description: 'Minimum confidence score (0-1) for a detection to be included. Higher values reduce false positives but may miss some valid detections.',
    recommendation: 'Start with 0.5 for most use cases. Increase to 0.7+ if you see too many false detections.',
  },

  // IOU Threshold
  iouThreshold: {
    title: 'IOU (Intersection over Union) Threshold',
    description: 'Used in Non-Maximum Suppression to remove duplicate detections. Higher values keep more overlapping boxes; lower values are more aggressive at removing duplicates.',
    recommendation: 'Default of 0.5 works well. Decrease to 0.3-0.4 if you see many duplicate detections on the same object.',
  },

  // Frame Skip
  frameSkip: {
    title: 'Frame Skip',
    description: 'Process every Nth frame from the video. Higher values mean faster processing but less temporal coverage.',
    values: {
      0: 'Process every frame (slowest, most complete)',
      1: 'Process every other frame',
      2: 'Process every 3rd frame',
      3: 'Process every 4th frame (faster)',
    },
    recommendation: 'For 30fps video, frame skip of 2-3 usually provides good coverage while significantly reducing processing time.',
  },

  // Diversity Filter
  diversityFilter: {
    title: 'Frame Diversity Filter',
    description: 'Automatically removes visually similar or low-motion frames during extraction. Reduces dataset redundancy and speeds up processing.',
    subSettings: {
      similarity: 'Visual similarity threshold (0-1). Higher values are stricter - frames must be more different to be kept. 0.85 is a good starting point.',
      motion: 'Minimum motion required between frames. Frames with less motion than this threshold are considered "static" and may be removed. 0.02 is a good default.',
    },
    recommendation: 'Enable for large datasets to automatically reduce redundancy. Disable if you need every frame regardless of similarity.',
  },

  // Batch Size
  batchSize: {
    title: 'Batch Size',
    description: 'Number of frames to process simultaneously on the GPU. Larger batches are more efficient but require more VRAM.',
    recommendation: 'Start with 4 for 8GB VRAM, 8 for 12GB+, or 16 for 24GB+. Reduce if you see out-of-memory errors.',
  },

  // Depth Mode
  depthMode: {
    title: 'Depth Computation Mode',
    description: 'Algorithm used to compute depth maps from stereo images.',
    modes: {
      NEURAL: 'AI-based depth estimation. Best quality but slowest. Requires GPU.',
      ULTRA: 'High-quality stereo matching. Good balance of quality and speed.',
      QUALITY: 'Standard stereo matching. Faster than ULTRA with good results.',
      PERFORMANCE: 'Fastest depth computation. Lower quality but real-time capable.',
    },
    recommendation: 'Use NEURAL for offline processing when quality matters. Use PERFORMANCE for quick previews.',
  },

  // Depth Range
  depthRange: {
    title: 'Depth Range',
    description: 'Minimum and maximum distance (in meters) for depth computation. Objects outside this range may have invalid depth.',
    recommendation: 'Set based on your capture environment. Indoor: 0.5-10m. Outdoor: 1-40m. Vehicle following: 2-100m.',
  },

  // Tracking
  tracking: {
    title: 'Object Tracking',
    description: 'Associate detections across frames to create persistent object tracks. Useful for temporal analysis and track-based filtering.',
    recommendation: 'Enable for video sequences where you want to track objects over time. Disable for single-frame analysis.',
  },

  // Object Classes
  objectClasses: {
    title: 'Object Classes to Detect',
    description: 'Select which types of objects to detect. Limiting classes can speed up processing and reduce noise.',
    categories: {
      vehicles: 'Cars, trucks, buses, motorcycles, bicycles',
      people: 'Pedestrians, cyclists, groups',
      animals: 'Dogs, cats, wildlife',
      infrastructure: 'Traffic signs, lights, barriers, cones',
    },
  },
} as const;

// =============================================================================
// Review & Curation Tooltips
// =============================================================================

export const REVIEW_TOOLTIPS = {
  diversity: {
    title: 'Diversity Analysis',
    description: 'Analyzes frames for visual similarity and motion to identify redundant data. Uses perceptual hashing (dHash) for similarity and frame differencing for motion.',
    interpretation: {
      similarFrames: 'Frames that look nearly identical. Often caused by stationary camera or slow movement.',
      lowMotion: 'Frames with minimal change from the previous frame. May indicate stopped vehicle or static scene.',
    },
  },

  classFilter: {
    title: 'Class Filtering',
    description: 'Exclude specific object classes from the curated dataset. Useful for removing unwanted detections like "background" or classes not relevant to your training goal.',
  },

  curatedDataset: {
    title: 'Curated Dataset',
    description: 'A snapshot of your review filters that can be used to create training exports. The filter configuration is saved and can be reused for consistent exports.',
    benefits: [
      'Reproducible - same filters produce same results',
      'Versioned - track changes to your curation over time',
      'Exportable - create multiple training datasets from one curation',
    ],
  },
} as const;

// =============================================================================
// Export Tooltips
// =============================================================================

export const EXPORT_TOOLTIPS = {
  format: {
    KITTI: 'KITTI dataset format. Widely supported for 2D/3D object detection. Uses image_2/, label_2/ directory structure.',
    COCO: 'COCO JSON format. Common for instance segmentation. Uses annotations.json with image references.',
  },

  splits: {
    title: 'Train/Val/Test Split',
    description: 'Divide data into training, validation, and test sets. Typical split is 80/10/10 or 70/15/15.',
    shuffleSeed: 'Random seed for reproducible shuffling. Using the same seed with the same data produces identical splits.',
  },

  lineageReport: {
    title: 'Lineage Report',
    description: 'Complete provenance information for your training dataset, tracing each frame back to its original SVO2 source file. Includes all transformation parameters for full reproducibility.',
  },
} as const;

// =============================================================================
// System Health Tooltips
// =============================================================================

export const SYSTEM_TOOLTIPS = {
  gpu: {
    title: 'GPU Status',
    description: 'Current GPU utilization and available VRAM. High utilization during processing is normal.',
  },

  worker: {
    title: 'Celery Worker',
    description: 'Background task processor status. Jobs require an active worker to process.',
  },

  disk: {
    title: 'Disk Usage',
    description: 'Available storage for datasets and exports. Each processed job can use 1-10GB depending on frame count.',
  },

  queue: {
    title: 'Job Queue',
    description: 'Number of jobs waiting to be processed. Jobs are processed in order they were submitted.',
  },
} as const;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format tooltip content with title and description
 */
export function formatTooltip(title: string, description: string): string {
  return `${title}\n\n${description}`;
}

/**
 * Format tooltip with recommendation
 */
export function formatTooltipWithRecommendation(
  title: string,
  description: string,
  recommendation: string
): string {
  return `${title}\n\n${description}\n\nRecommended: ${recommendation}`;
}
