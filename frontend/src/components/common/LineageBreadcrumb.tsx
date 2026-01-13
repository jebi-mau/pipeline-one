/**
 * Lineage Breadcrumb Component
 * Displays: Dataset > SVO2 File > Frame > Annotation
 * Each segment is clickable to navigate to its detail view.
 */

import { Link } from 'react-router-dom';
import type { LineageBreadcrumbSegment } from '../../types/lineage';

interface LineageBreadcrumbProps {
  segments: LineageBreadcrumbSegment[];
  className?: string;
}

const segmentIcons: Record<string, string> = {
  dataset: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
  svo2: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
  frame: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
  annotation: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z',
};

const segmentColors: Record<string, string> = {
  dataset: 'text-blue-400 hover:text-blue-300',
  svo2: 'text-green-400 hover:text-green-300',
  frame: 'text-purple-400 hover:text-purple-300',
  annotation: 'text-orange-400 hover:text-orange-300',
};

export function LineageBreadcrumb({ segments, className = '' }: LineageBreadcrumbProps) {
  if (segments.length === 0) {
    return null;
  }

  return (
    <nav className={`flex items-center text-sm ${className}`} aria-label="Lineage breadcrumb">
      {segments.map((segment, index) => (
        <div key={`${segment.type}-${segment.id}`} className="flex items-center">
          {index > 0 && (
            <svg
              className="w-4 h-4 mx-2 text-gray-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
          )}
          <Link
            to={segment.path}
            className={`flex items-center gap-1.5 ${segmentColors[segment.type]} transition-colors`}
            title={`View ${segment.type} details`}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d={segmentIcons[segment.type]}
              />
            </svg>
            <span className="max-w-[200px] truncate">{segment.label}</span>
          </Link>
        </div>
      ))}
    </nav>
  );
}

// Helper function to build breadcrumb segments from lineage data
export function buildBreadcrumbFromFrameLineage(
  frameLineage: {
    frame: { id: string; sequence_index: number };
    dataset_file?: { id: string; original_filename: string } | null;
    dataset?: { id: string; name: string } | null;
  }
): LineageBreadcrumbSegment[] {
  const segments: LineageBreadcrumbSegment[] = [];

  if (frameLineage.dataset) {
    segments.push({
      type: 'dataset',
      id: frameLineage.dataset.id,
      label: frameLineage.dataset.name,
      path: `/datasets/${frameLineage.dataset.id}`,
    });
  }

  if (frameLineage.dataset_file) {
    segments.push({
      type: 'svo2',
      id: frameLineage.dataset_file.id,
      label: frameLineage.dataset_file.original_filename,
      path: `/svo2/${frameLineage.dataset_file.id}`,
    });
  }

  segments.push({
    type: 'frame',
    id: frameLineage.frame.id,
    label: `Frame ${frameLineage.frame.sequence_index}`,
    path: `/frames/${frameLineage.frame.id}`,
  });

  return segments;
}

export function buildBreadcrumbFromAnnotationLineage(
  annotationLineage: {
    annotation: { id: string; label: string };
    frame?: { id: string; sequence_index: number } | null;
    svo2_file?: { id: string; original_filename: string } | null;
    dataset?: { id: string; name: string } | null;
  }
): LineageBreadcrumbSegment[] {
  const segments: LineageBreadcrumbSegment[] = [];

  if (annotationLineage.dataset) {
    segments.push({
      type: 'dataset',
      id: annotationLineage.dataset.id,
      label: annotationLineage.dataset.name,
      path: `/datasets/${annotationLineage.dataset.id}`,
    });
  }

  if (annotationLineage.svo2_file) {
    segments.push({
      type: 'svo2',
      id: annotationLineage.svo2_file.id,
      label: annotationLineage.svo2_file.original_filename,
      path: `/svo2/${annotationLineage.svo2_file.id}`,
    });
  }

  if (annotationLineage.frame) {
    segments.push({
      type: 'frame',
      id: annotationLineage.frame.id,
      label: `Frame ${annotationLineage.frame.sequence_index}`,
      path: `/frames/${annotationLineage.frame.id}`,
    });
  }

  segments.push({
    type: 'annotation',
    id: annotationLineage.annotation.id,
    label: annotationLineage.annotation.label,
    path: `/annotations/${annotationLineage.annotation.id}`,
  });

  return segments;
}
