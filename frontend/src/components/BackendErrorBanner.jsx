import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export const BackendErrorBanner = ({ error, onRetry, isRetrying = false }) => {
  if (!error) return null;

  return (
    <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-xs text-rose-300 flex flex-wrap items-center justify-between gap-3 shadow-md animate-in fade-in duration-200">
      <div className="flex items-center gap-2.5 min-w-0">
        <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
        <div>
          <span className="font-bold text-rose-200">Backend Communication Issue</span>
          <p className="text-[11px] text-rose-300/80 mt-0.5 truncate max-w-xl">
            {error || 'Cannot reach FastAPI service at http://localhost:8000.'}
          </p>
        </div>
      </div>

      <button
        onClick={onRetry}
        disabled={isRetrying}
        className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shrink-0 shadow-sm"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
        <span>{isRetrying ? 'Reconnecting...' : 'Retry Connection'}</span>
      </button>
    </div>
  );
};
