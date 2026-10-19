import React, { useState } from 'react';
import { Lock, Server, Key, Users, Radio, Database, RefreshCw, CheckCircle2 } from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { formatIndianNumber } from '../utils/formatters';

export const AdminPanel = () => {
  const { wsStatus, backendHealth, checkHealth, healthLoading } = useFilter();
  const [copied, setCopied] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-slate-100 text-teal-600 rounded-xl border border-slate-200">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">System Administration & Infrastructure</h2>
            <p className="text-xs text-slate-400">
              API runtime environment, database engine status, and engine telemetry
            </p>
          </div>
        </div>

        <button
          onClick={() => checkHealth()}
          className="px-3.5 py-2 bg-slate-100 hover:bg-slate-700 border border-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${healthLoading ? 'animate-spin' : ''}`} />
          <span>Refresh System Health</span>
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Server className="w-4 h-4 text-teal-600" />
            <h4 className="text-xs font-bold text-slate-600">FastAPI Backend</h4>
          </div>
          <p className="text-lg font-extrabold text-emerald-600">
            {backendHealth?.status === 'healthy' ? 'Online & Healthy' : 'Degraded / Connecting'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Service: {backendHealth?.service || 'VaultGuard'}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Radio className="w-4 h-4 text-blue-500" />
            <h4 className="text-xs font-bold text-slate-600">WebSocket Streamer</h4>
          </div>
          <p className={`text-lg font-extrabold ${wsStatus === 'connected' ? 'text-teal-600' : 'text-slate-400'}`}>
            {wsStatus === 'connected' ? 'Connected (Live)' : wsStatus === 'reconnecting' ? 'Reconnecting' : 'Disconnected'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Endpoint: /ws/transactions (~3s simulated intervals)
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-purple-400" />
            <h4 className="text-xs font-bold text-slate-600">SQLite Storage</h4>
          </div>
          <p className="text-lg font-extrabold text-slate-800">vaultguard.db</p>
          <p className="text-[11px] text-slate-400 mt-1">
            {backendHealth ? `${formatIndianNumber(backendHealth.transaction_count)} transaction records` : 'Record count unavailable'}
          </p>
        </div>
      </div>

      {/* Runtime Configuration Info */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
        <h3 className="text-sm font-bold text-slate-800">Runtime Environment Configuration</h3>

        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
          <div className="flex justify-between items-center pb-2 border-b border-slate-200">
            <span className="text-slate-400 font-medium">Model Version:</span>
            <span className="font-mono text-teal-600 font-bold">{backendHealth?.model_version || 'Unavailable'}</span>
          </div>

          <div className="flex justify-between items-center pb-2 border-b border-slate-200">
            <span className="text-slate-400 font-medium">ML Artifacts Integrity:</span>
            <span className="font-mono text-emerald-600 font-bold">{backendHealth?.ml_artifacts || 'Unavailable'}</span>
          </div>

          <div className="flex justify-between items-center pb-2 border-b border-slate-200">
            <span className="text-slate-400 font-medium">Database Connection:</span>
            <span className="font-mono text-emerald-600 font-bold">{backendHealth?.database || 'Unavailable'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400 font-medium">Frontend API Base URL:</span>
            <span className="font-mono text-slate-600">{import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
