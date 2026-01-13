/**
 * Pipeline One - Review mode state store using Zustand
 */

import { create } from 'zustand';
import type {
  DiversityAnalysisResponse,
  FilterConfiguration,
  FrameThumbnail,
  PlaybackSpeed,
} from '../types/review';

interface ReviewState {
  // Current job context
  jobId: string | null;
  frames: FrameThumbnail[];
  totalFrames: number;

  // Playback state
  currentFrameIndex: number;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;

  // Filter configuration
  excludedClasses: Set<string>;
  excludedAnnotationIds: Set<string>;
  excludedFrameIndices: Set<number>;
  diversityApplied: boolean;
  similarityThreshold: number;
  motionThreshold: number;

  // Diversity analysis results
  diversityStatus: 'idle' | 'analyzing' | 'complete' | 'failed';
  diversityResults: DiversityAnalysisResponse | null;

  // Export modal
  isExportModalOpen: boolean;

  // Actions - Job context
  setJobId: (jobId: string | null) => void;
  setFrames: (frames: FrameThumbnail[], total: number) => void;

  // Actions - Playback
  setCurrentFrameIndex: (index: number) => void;
  stepForward: () => void;
  stepBackward: () => void;
  togglePlayback: () => void;
  setPlaying: (playing: boolean) => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;

  // Actions - Filtering
  toggleClassFilter: (className: string) => void;
  setClassExcluded: (className: string, excluded: boolean) => void;
  toggleAnnotationFilter: (annotationId: string) => void;
  setAnnotationExcluded: (annotationId: string, excluded: boolean) => void;
  setExcludedFrameIndices: (indices: number[]) => void;
  setDiversityThresholds: (similarity: number, motion: number) => void;
  applyDiversity: (apply: boolean) => void;

  // Actions - Diversity
  setDiversityStatus: (status: 'idle' | 'analyzing' | 'complete' | 'failed') => void;
  setDiversityResults: (results: DiversityAnalysisResponse | null) => void;

  // Actions - Export
  openExportModal: () => void;
  closeExportModal: () => void;

  // Computed
  getFilterConfig: () => FilterConfiguration;
  getSelectedFrameCount: () => number;
  resetFilters: () => void;
  resetAll: () => void;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  // Initial state
  jobId: null,
  frames: [],
  totalFrames: 0,
  currentFrameIndex: 0,
  isPlaying: false,
  playbackSpeed: 1,
  excludedClasses: new Set<string>(),
  excludedAnnotationIds: new Set<string>(),
  excludedFrameIndices: new Set<number>(),
  diversityApplied: false,
  similarityThreshold: 0.85,
  motionThreshold: 0.02,
  diversityStatus: 'idle',
  diversityResults: null,
  isExportModalOpen: false,

  // Job context actions
  setJobId: (jobId) =>
    set({
      jobId,
      frames: [],
      totalFrames: 0,
      currentFrameIndex: 0,
      isPlaying: false,
      diversityStatus: 'idle',
      diversityResults: null,
    }),

  setFrames: (frames, total) =>
    set({
      frames,
      totalFrames: total,
    }),

  // Playback actions
  setCurrentFrameIndex: (index) =>
    set((state) => ({
      currentFrameIndex: Math.max(0, Math.min(index, state.totalFrames - 1)),
    })),

  stepForward: () =>
    set((state) => ({
      currentFrameIndex: Math.min(state.currentFrameIndex + 1, state.totalFrames - 1),
    })),

  stepBackward: () =>
    set((state) => ({
      currentFrameIndex: Math.max(state.currentFrameIndex - 1, 0),
    })),

  togglePlayback: () =>
    set((state) => ({
      isPlaying: !state.isPlaying,
    })),

  setPlaying: (playing) => set({ isPlaying: playing }),

  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),

  // Filtering actions
  toggleClassFilter: (className) =>
    set((state) => {
      const newSet = new Set(state.excludedClasses);
      if (newSet.has(className)) {
        newSet.delete(className);
      } else {
        newSet.add(className);
      }
      return { excludedClasses: newSet };
    }),

  setClassExcluded: (className, excluded) =>
    set((state) => {
      const newSet = new Set(state.excludedClasses);
      if (excluded) {
        newSet.add(className);
      } else {
        newSet.delete(className);
      }
      return { excludedClasses: newSet };
    }),

  toggleAnnotationFilter: (annotationId) =>
    set((state) => {
      const newSet = new Set(state.excludedAnnotationIds);
      if (newSet.has(annotationId)) {
        newSet.delete(annotationId);
      } else {
        newSet.add(annotationId);
      }
      return { excludedAnnotationIds: newSet };
    }),

  setAnnotationExcluded: (annotationId, excluded) =>
    set((state) => {
      const newSet = new Set(state.excludedAnnotationIds);
      if (excluded) {
        newSet.add(annotationId);
      } else {
        newSet.delete(annotationId);
      }
      return { excludedAnnotationIds: newSet };
    }),

  setExcludedFrameIndices: (indices) =>
    set({ excludedFrameIndices: new Set(indices) }),

  setDiversityThresholds: (similarity, motion) =>
    set({
      similarityThreshold: similarity,
      motionThreshold: motion,
    }),

  applyDiversity: (apply) =>
    set((state) => {
      if (apply && state.diversityResults) {
        return {
          diversityApplied: true,
          excludedFrameIndices: new Set(state.diversityResults.excluded_frame_indices),
        };
      }
      return {
        diversityApplied: false,
        excludedFrameIndices: new Set(),
      };
    }),

  // Diversity actions
  setDiversityStatus: (status) => set({ diversityStatus: status }),

  setDiversityResults: (results) =>
    set({
      diversityResults: results,
      diversityStatus: results ? 'complete' : 'idle',
    }),

  // Export actions
  openExportModal: () => set({ isExportModalOpen: true }),
  closeExportModal: () => set({ isExportModalOpen: false }),

  // Computed values
  getFilterConfig: () => {
    const state = get();
    return {
      excluded_classes: Array.from(state.excludedClasses),
      excluded_annotation_ids: Array.from(state.excludedAnnotationIds),
      excluded_frame_indices: Array.from(state.excludedFrameIndices),
      diversity_applied: state.diversityApplied,
      similarity_threshold: state.diversityApplied ? state.similarityThreshold : null,
      motion_threshold: state.diversityApplied ? state.motionThreshold : null,
    };
  },

  getSelectedFrameCount: () => {
    const state = get();
    return state.totalFrames - state.excludedFrameIndices.size;
  },

  // Reset actions
  resetFilters: () =>
    set({
      excludedClasses: new Set<string>(),
      excludedAnnotationIds: new Set<string>(),
      excludedFrameIndices: new Set<number>(),
      diversityApplied: false,
    }),

  resetAll: () =>
    set({
      jobId: null,
      frames: [],
      totalFrames: 0,
      currentFrameIndex: 0,
      isPlaying: false,
      playbackSpeed: 1,
      excludedClasses: new Set<string>(),
      excludedAnnotationIds: new Set<string>(),
      excludedFrameIndices: new Set<number>(),
      diversityApplied: false,
      similarityThreshold: 0.85,
      motionThreshold: 0.02,
      diversityStatus: 'idle',
      diversityResults: null,
      isExportModalOpen: false,
    }),
}));
