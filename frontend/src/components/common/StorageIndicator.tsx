/**
 * Compact storage indicator for the main header
 * Shows disk usage with color-coded warnings
 */

import { useEffect, useState } from 'react';
import { CircleStackIcon } from '@heroicons/react/24/outline';
import { storageService } from '../../services/storageService';
import type { StorageSummary } from '../../types/storage';

interface StorageIndicatorProps {
  onClick?: () => void;
  className?: string;
}

export function StorageIndicator({ onClick, className = '' }: StorageIndicatorProps) {
  const [storage, setStorage] = useState<StorageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStorage();
    // Refresh every 60 seconds
    const interval = setInterval(loadStorage, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadStorage = async () => {
    try {
      const data = await storageService.getStorageSummary();
      setStorage(data);
      setError(null);
    } catch (err) {
      setError('Failed to load storage');
      console.error('Failed to load storage summary:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center gap-2 text-secondary-400 ${className}`}>
        <CircleStackIcon className="w-4 h-4 animate-pulse" />
        <span className="text-sm">...</span>
      </div>
    );
  }

  if (error || !storage) {
    return (
      <div className={`flex items-center gap-2 text-secondary-500 ${className}`}>
        <CircleStackIcon className="w-4 h-4" />
        <span className="text-sm">--</span>
      </div>
    );
  }

  // Determine color based on warning level
  const getStatusColor = () => {
    switch (storage.warning_level) {
      case 'critical':
        return 'text-red-400';
      case 'warning':
        return 'text-yellow-400';
      default:
        return 'text-secondary-400';
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
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-secondary-800 transition-colors ${className}`}
      title={storage.warning || `${storage.disk_free_formatted} free`}
    >
      <CircleStackIcon className={`w-4 h-4 ${getStatusColor()}`} />

      {/* Progress bar */}
      <div className="w-16 h-1.5 bg-secondary-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getProgressColor()} transition-all duration-300`}
          style={{ width: `${Math.min(storage.disk_usage_percent, 100)}%` }}
        />
      </div>

      <span className={`text-xs font-medium ${getStatusColor()}`}>
        {storage.disk_usage_percent.toFixed(0)}%
      </span>
    </button>
  );
}
