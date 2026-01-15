/**
 * Storage Dashboard component for viewing and managing disk usage
 */

import { useEffect, useState } from 'react';
import {
  CircleStackIcon,
  FolderIcon,
  ServerIcon,
  TrashIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { storageService } from '../../services/storageService';
import type { StorageSummary, OrphanedDirectoriesResponse, CleanupResult } from '../../types/storage';

export function StorageDashboard() {
  const [storage, setStorage] = useState<StorageSummary | null>(null);
  const [orphans, setOrphans] = useState<OrphanedDirectoriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [storageData, orphansData] = await Promise.all([
        storageService.getStorageSummary(),
        storageService.listOrphanedDirectories(),
      ]);
      setStorage(storageData);
      setOrphans(orphansData);
    } catch (err) {
      setError('Failed to load storage data');
      console.error('Failed to load storage data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCleanOrphans = async () => {
    if (!confirm('Are you sure you want to delete all orphaned directories? This cannot be undone.')) {
      return;
    }

    setCleanupLoading(true);
    setCleanupResult(null);
    try {
      const result = await storageService.deleteOrphanedDirectories();
      setCleanupResult(result);
      // Reload data to update counts
      await loadData();
    } catch (err) {
      setError('Failed to clean up orphaned directories');
      console.error('Cleanup failed:', err);
    } finally {
      setCleanupLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <ArrowPathIcon className="w-6 h-6 text-secondary-400 animate-spin" />
        <span className="ml-2 text-secondary-400">Loading storage data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
        <div className="flex items-center gap-2 text-red-400">
          <ExclamationCircleIcon className="w-5 h-5" />
          <span>{error}</span>
        </div>
        <button
          onClick={loadData}
          className="mt-2 text-sm text-red-300 hover:text-red-200"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!storage) return null;

  const getWarningIcon = () => {
    switch (storage.warning_level) {
      case 'critical':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-400" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400" />;
      default:
        return <CheckCircleIcon className="w-5 h-5 text-green-400" />;
    }
  };

  const getProgressColor = () => {
    switch (storage.warning_level) {
      case 'critical':
        return 'bg-red-500';
      case 'warning':
        return 'bg-yellow-500';
      default:
        return 'bg-accent-500';
    }
  };

  return (
    <div className="space-y-6" id="storage">
      {/* Disk Usage Overview */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-secondary-100 flex items-center gap-2">
            <CircleStackIcon className="w-5 h-5" />
            Disk Usage
          </h3>
          <button
            onClick={loadData}
            className="p-2 text-secondary-400 hover:text-secondary-200 transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Warning Banner */}
        {storage.warning && (
          <div
            className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${
              storage.warning_level === 'critical'
                ? 'bg-red-500/10 border border-red-500/30 text-red-300'
                : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-300'
            }`}
          >
            {getWarningIcon()}
            <span>{storage.warning}</span>
          </div>
        )}

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-secondary-400">
              {storage.disk_used_formatted} used of {storage.disk_total_formatted}
            </span>
            <span className="text-secondary-300 font-medium">
              {storage.disk_usage_percent}%
            </span>
          </div>
          <div className="h-3 bg-secondary-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${getProgressColor()} transition-all duration-300`}
              style={{ width: `${Math.min(storage.disk_usage_percent, 100)}%` }}
            />
          </div>
          <div className="text-right text-sm text-secondary-500 mt-1">
            {storage.disk_free_formatted} free
          </div>
        </div>

        {/* Storage Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-secondary-800/50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-secondary-400 mb-2">
              <FolderIcon className="w-4 h-4" />
              <span className="text-sm">Processing Jobs</span>
            </div>
            <p className="text-xl font-semibold text-secondary-100">
              {storage.total_jobs_storage_formatted}
            </p>
          </div>

          <div className="bg-secondary-800/50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-secondary-400 mb-2">
              <ServerIcon className="w-4 h-4" />
              <span className="text-sm">Datasets</span>
            </div>
            <p className="text-xl font-semibold text-secondary-100">
              {storage.total_datasets_storage_formatted}
            </p>
          </div>

          <div className="bg-secondary-800/50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-secondary-400 mb-2">
              <ServerIcon className="w-4 h-4" />
              <span className="text-sm">Training Datasets</span>
            </div>
            <p className="text-xl font-semibold text-secondary-100">
              {storage.total_training_datasets_formatted}
            </p>
          </div>
        </div>
      </div>

      {/* Orphaned Directories */}
      {orphans && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-secondary-100 flex items-center gap-2">
              <TrashIcon className="w-5 h-5" />
              Orphaned Directories
            </h3>
            {orphans.orphaned_count > 0 && (
              <button
                onClick={handleCleanOrphans}
                disabled={cleanupLoading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50"
              >
                {cleanupLoading ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <TrashIcon className="w-4 h-4" />
                )}
                Delete All
              </button>
            )}
          </div>

          <p className="text-sm text-secondary-400 mb-4">
            Orphaned directories exist on disk but have no corresponding database record.
            They can be safely deleted to free up space.
          </p>

          {/* Cleanup Result */}
          {cleanupResult && (
            <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
              <div className="flex items-center gap-2 text-green-300">
                <CheckCircleIcon className="w-5 h-5" />
                <span>
                  Deleted {cleanupResult.deleted_count} directories, freed{' '}
                  {cleanupResult.deleted_size_human}
                </span>
              </div>
              {cleanupResult.errors.length > 0 && (
                <div className="mt-2 text-sm text-red-300">
                  {cleanupResult.errors.length} error(s) occurred
                </div>
              )}
            </div>
          )}

          {orphans.orphaned_count === 0 ? (
            <div className="text-center py-8 text-secondary-500">
              <CheckCircleIcon className="w-8 h-8 mx-auto mb-2 text-green-400" />
              <p>No orphaned directories found</p>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between text-sm text-secondary-400 mb-2">
                <span>{orphans.orphaned_count} orphaned directories</span>
                <span>Total: {orphans.total_size_human}</span>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {orphans.orphans.map((orphan) => (
                  <div
                    key={orphan.name}
                    className="flex items-center justify-between py-2 px-3 bg-secondary-800/50 rounded text-sm"
                  >
                    <span className="text-secondary-300 font-mono truncate">
                      {orphan.name}
                    </span>
                    <span className="text-secondary-500 ml-4 whitespace-nowrap">
                      {orphan.size_human}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
