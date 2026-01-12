/**
 * Shalom - Error message component
 */

import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ title = 'Error', message, onRetry }: ErrorMessageProps) {
  return (
    <div className="card p-6 border border-red-500/50">
      <div className="flex items-start space-x-3">
        <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-400">{title}</h3>
          <p className="mt-1 text-sm text-secondary-400">{message}</p>
          {onRetry && (
            <button onClick={onRetry} className="btn-secondary mt-3 text-sm">
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
