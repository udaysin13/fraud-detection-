import React from 'react';
import { Lock, Server, Key, Users, Radio, Database } from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const AdminPanel = () => {
  const { wsConnected } = useFilter();

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-slate-100 text-slate-800 rounded-xl">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Admin System Controls</h2>
            <p className="text-xs text-slate-500">System configuration, API keys, role access, and audit trail</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Server className="w-4 h-4 text-orange-500" />
            <h4 className="text-xs font-bold text-slate-900">FastAPI Backend Status</h4>
          </div>
          <p className="text-lg font-extrabold text-emerald-600">Online (Port 8000)</p>
          <p className="text-xs text-slate-400 mt-1">Uvicorn worker active</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Radio className="w-4 h-4 text-teal-500" />
            <h4 className="text-xs font-bold text-slate-900">WebSocket Streamer</h4>
          </div>
          <p className="text-lg font-extrabold text-slate-900">
            {wsConnected ? 'Connected (ws://)' : 'Disconnected'}
          </p>
          <p className="text-xs text-slate-400 mt-1">Simulated live feed 3s interval</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-indigo-500" />
            <h4 className="text-xs font-bold text-slate-900">SQLite Storage</h4>
          </div>
          <p className="text-lg font-extrabold text-slate-900">vaultguard.db</p>
          <p className="text-xs text-slate-400 mt-1">55,000 scored records stored</p>
        </div>
      </div>

      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5 space-y-4">
        <h3 className="text-base font-bold text-slate-900">API Credentials & Keys</h3>

        <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl flex justify-between items-center text-xs">
          <div>
            <p className="font-bold text-slate-900">Master Secret API Key</p>
            <p className="font-mono text-slate-500 text-[11px]">vg_live_98a7f10b284c19a904e28</p>
          </div>
          <button
            onClick={() => alert('API Key copied to clipboard.')}
            className="px-3 py-1.5 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800"
          >
            Copy Key
          </button>
        </div>
      </div>
    </div>
  );
};
