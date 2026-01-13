/**
 * Error Boundary component for catching and handling React errors
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call optional error callback
    this.props.onError?.(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[200px] flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="mx-auto w-12 h-12 rounded-full bg-red-900/50 flex items-center justify-center mb-4">
              <ExclamationTriangleIcon className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-secondary-100 mb-2">
              Something went wrong
            </h3>
            <p className="text-sm text-secondary-400 mb-4">
              An unexpected error occurred. Please try again or refresh the page.
            </p>
            {this.state.error && (
              <details className="text-left mb-4">
                <summary className="text-xs text-secondary-500 cursor-pointer hover:text-secondary-400">
                  Error details
                </summary>
                <pre className="mt-2 p-3 bg-secondary-800 rounded-lg text-xs text-red-400 overflow-auto max-h-32">
                  {this.state.error.message}
                  {this.state.errorInfo?.componentStack && (
                    <span className="text-secondary-500">
                      {this.state.errorInfo.componentStack}
                    </span>
                  )}
                </pre>
              </details>
            )}
            <div className="flex justify-center gap-3">
              <button
                onClick={this.handleReset}
                className="btn-secondary flex items-center gap-2"
              >
                <ArrowPathIcon className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component to wrap a component with ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  const WithErrorBoundary: React.FC<P> = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundary.displayName = `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return WithErrorBoundary;
}
