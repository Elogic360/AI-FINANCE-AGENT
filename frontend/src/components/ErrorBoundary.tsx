import { Component, ErrorInfo, ReactNode } from 'react';
import { useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { extractErrorMessage } from '../lib/api';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: unknown;
}

/**
 * ErrorBoundary catches React rendering errors and displays a
 * user-friendly fallback UI with a retry button.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const message = safeErrorMessage(this.state.error);

      return (
        <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] p-6">
          <div className="max-w-md w-full bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-[#e4e4ed] mb-2">
              Something went wrong
            </h2>
            <p className="text-[#8888a0] text-sm mb-6">
              {message}
            </p>
            {process.env.NODE_ENV === 'development' && (
              <pre className="text-xs text-red-400 bg-[#0a0a0f] rounded-lg p-3 mb-4 text-left overflow-auto max-h-32 whitespace-pre-wrap">
                {devErrorDetail(this.state.error)}
              </pre>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-[#0a0a0f] font-medium rounded-lg transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => (window.location.href = '/dashboard')}
                className="px-5 py-2.5 bg-[#2a2a3e] hover:bg-[#3a3a4e] text-[#e4e4ed] font-medium rounded-lg transition-colors"
              >
                Go to Dashboard
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
 * React Router error boundary for route-level errors.
 * Renders inside route errorElement props.
 */
export function RouteErrorElement(): ReactNode {
  const error = useRouteError();

  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : safeErrorMessage(error);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] p-6">
      <div className="max-w-md w-full bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
          <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-[#e4e4ed] mb-2">
          {isRouteErrorResponse(error) ? `Error ${error.status}` : 'Something went wrong'}
        </h2>
        <p className="text-[#8888a0] text-sm mb-6">{message}</p>
        {process.env.NODE_ENV === 'development' && (
          <pre className="text-xs text-red-400 bg-[#0a0a0f] rounded-lg p-3 mb-4 text-left overflow-auto max-h-32 whitespace-pre-wrap">
            {devErrorDetail(error)}
          </pre>
        )}
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => window.location.reload()}
            className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-[#0a0a0f] font-medium rounded-lg transition-colors"
          >
            Reload Page
          </button>
          <button
            onClick={() => (window.location.href = '/dashboard')}
            className="px-5 py-2.5 bg-[#2a2a3e] hover:bg-[#3a3a4e] text-[#e4e4ed] font-medium rounded-lg transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Safely extract a human-readable string from any error value.
 * Never returns an object — always a renderable string.
 */
function safeErrorMessage(error: unknown): string {
  if (error == null) return 'An unexpected error occurred.';
  if (typeof error === 'string') return error || 'An unexpected error occurred.';

  // Route response errors
  if (typeof error === 'object' && 'statusText' in error) {
    const routeErr = error as { status?: number; statusText?: string; data?: unknown };
    return routeErr.statusText || `HTTP ${routeErr.status ?? 'Unknown'}`;
  }

  // Standard Error
  if (error instanceof Error) return error.message || 'An unexpected error occurred.';

  // FastAPI / Axios error shapes — delegate to extractErrorMessage
  if (typeof error === 'object' && 'response' in error) {
    return extractErrorMessage(error, 'An unexpected error occurred.');
  }

  // Plain object with a msg field (Pydantic validation error item)
  if (typeof error === 'object' && 'msg' in error && typeof (error as Record<string, unknown>).msg === 'string') {
    return (error as Record<string, unknown>).msg as string;
  }

  try { return JSON.stringify(error); } catch { return 'An unexpected error occurred.'; }
}

function devErrorDetail(error: unknown): string {
  if (error == null) return 'No error details available.';

  if (error instanceof Error) {
    return `${error.name}: ${error.message}${error.stack ? `\n${error.stack}` : ''}`;
  }

  try { return JSON.stringify(error, null, 2); } catch { return String(error); }
}

export default ErrorBoundary;
