/**
 * Annotation Matching Dashboard
 * Shows:
 * - Import summary per SVO2 file
 * - Matched vs unmatched counts
 * - Unmatched annotation list with source filenames
 * - Match statistics visualization
 */

import { useEffect, useState } from 'react';
import { LoadingSpinner, ErrorMessage } from '../common';
import api from '../../services/api';

interface AnnotationImport {
  id: string;
  source_tool: string;
  source_format: string;
  source_filename: string;
  status: string;
  total_images: number;
  matched_frames: number;
  unmatched_images: number;
  total_annotations: number;
  imported_at: string | null;
  completed_at: string | null;
}

interface UnmatchedAnnotation {
  id: string;
  source_image_name: string;
  label: string;
  annotation_type: string;
}

interface AnnotationMatchingViewProps {
  datasetId: string;
}

export function AnnotationMatchingView({ datasetId }: AnnotationMatchingViewProps) {
  const [imports, setImports] = useState<AnnotationImport[]>([]);
  const [selectedImportId, setSelectedImportId] = useState<string | null>(null);
  const [unmatchedAnnotations, setUnmatchedAnnotations] = useState<UnmatchedAnnotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingUnmatched, setLoadingUnmatched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch annotation imports for this dataset
  useEffect(() => {
    async function fetchImports() {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get(`/datasets/${datasetId}/annotations/imports`);
        setImports(response.data.imports || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load annotation imports');
      } finally {
        setLoading(false);
      }
    }

    fetchImports();
  }, [datasetId]);

  // Fetch unmatched annotations when an import is selected
  useEffect(() => {
    if (!selectedImportId) {
      setUnmatchedAnnotations([]);
      return;
    }

    async function fetchUnmatched() {
      setLoadingUnmatched(true);
      try {
        const response = await api.get(`/annotations/imports/${selectedImportId}/unmatched`);
        setUnmatchedAnnotations(response.data.annotations || []);
      } catch (err) {
        console.error('Failed to load unmatched annotations:', err);
        setUnmatchedAnnotations([]);
      } finally {
        setLoadingUnmatched(false);
      }
    }

    fetchUnmatched();
  }, [selectedImportId]);

  // Calculate totals
  const totalStats = imports.reduce(
    (acc, imp) => ({
      totalImages: acc.totalImages + imp.total_images,
      matched: acc.matched + imp.matched_frames,
      unmatched: acc.unmatched + imp.unmatched_images,
      totalAnnotations: acc.totalAnnotations + imp.total_annotations,
    }),
    { totalImages: 0, matched: 0, unmatched: 0, totalAnnotations: 0 }
  );

  const matchRate =
    totalStats.totalImages > 0
      ? ((totalStats.matched / totalStats.totalImages) * 100).toFixed(1)
      : '0';

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (imports.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <svg
          className="w-16 h-16 mx-auto mb-4 text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
          />
        </svg>
        <h3 className="text-lg font-medium text-white mb-2">No Annotation Imports</h3>
        <p>Import annotations from CVAT or other tools to see matching statistics.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-700/50 rounded-lg p-4">
          <p className="text-sm text-gray-400">Total Images</p>
          <p className="text-2xl font-bold text-white">{totalStats.totalImages}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-4">
          <p className="text-sm text-gray-400">Matched Frames</p>
          <p className="text-2xl font-bold text-green-400">{totalStats.matched}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-4">
          <p className="text-sm text-gray-400">Unmatched</p>
          <p className="text-2xl font-bold text-orange-400">{totalStats.unmatched}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-4">
          <p className="text-sm text-gray-400">Match Rate</p>
          <p className="text-2xl font-bold text-primary-400">{matchRate}%</p>
        </div>
      </div>

      {/* Match Rate Bar */}
      <div className="bg-gray-700/50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Overall Match Rate</span>
          <span className="text-sm text-white">{totalStats.matched} / {totalStats.totalImages}</span>
        </div>
        <div className="h-3 bg-gray-600 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500"
            style={{ width: `${matchRate}%` }}
          />
        </div>
      </div>

      {/* Import Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Annotation Imports</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm bg-gray-700/30">
                <th className="px-4 py-3">Source File</th>
                <th className="px-4 py-3">Tool</th>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Matched</th>
                <th className="px-4 py-3">Unmatched</th>
                <th className="px-4 py-3">Annotations</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((imp) => {
                const impMatchRate =
                  imp.total_images > 0
                    ? ((imp.matched_frames / imp.total_images) * 100).toFixed(0)
                    : '0';

                return (
                  <tr
                    key={imp.id}
                    className={`border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors ${
                      selectedImportId === imp.id ? 'bg-gray-700/50' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-white">{imp.source_filename}</td>
                    <td className="px-4 py-3 text-gray-300">{imp.source_tool}</td>
                    <td className="px-4 py-3 text-gray-300 uppercase text-sm">{imp.source_format}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-xs ${
                          imp.status === 'completed'
                            ? 'bg-green-500/20 text-green-400'
                            : imp.status === 'failed'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-yellow-500/20 text-yellow-400'
                        }`}
                      >
                        {imp.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-green-400">{imp.matched_frames}</span>
                      <span className="text-gray-500 mx-1">/</span>
                      <span className="text-gray-300">{imp.total_images}</span>
                      <span className="text-gray-500 ml-2">({impMatchRate}%)</span>
                    </td>
                    <td className="px-4 py-3">
                      {imp.unmatched_images > 0 ? (
                        <span className="text-orange-400">{imp.unmatched_images}</span>
                      ) : (
                        <span className="text-gray-500">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{imp.total_annotations}</td>
                    <td className="px-4 py-3">
                      {imp.unmatched_images > 0 && (
                        <button
                          onClick={() =>
                            setSelectedImportId(selectedImportId === imp.id ? null : imp.id)
                          }
                          className="text-primary-400 hover:text-primary-300 text-sm"
                        >
                          {selectedImportId === imp.id ? 'Hide Unmatched' : 'View Unmatched'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unmatched Annotations Panel */}
      {selectedImportId && (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Unmatched Annotations</h3>
            <button
              onClick={() => setSelectedImportId(null)}
              className="text-gray-400 hover:text-white"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {loadingUnmatched ? (
            <div className="flex items-center justify-center p-8">
              <LoadingSpinner />
            </div>
          ) : unmatchedAnnotations.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No unmatched annotations found.
            </div>
          ) : (
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-gray-700">
                  <tr className="text-left text-gray-400 text-sm">
                    <th className="px-4 py-2">Source Image</th>
                    <th className="px-4 py-2">Label</th>
                    <th className="px-4 py-2">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {unmatchedAnnotations.map((ann) => (
                    <tr key={ann.id} className="border-b border-gray-700/50">
                      <td className="px-4 py-2 text-gray-300 font-mono text-sm">
                        {ann.source_image_name}
                      </td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-primary-500/20 text-primary-400 text-sm">
                          {ann.label}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-400 text-sm">{ann.annotation_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AnnotationMatchingView;
