import React from 'react';
import { X, ShieldAlert, Clock, User, Tag, CheckCircle2 } from 'lucide-react';

export const AlertDetailDrawer = ({ alert, onClose, onUpdateStatus }) => {
  if (!alert) return null;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Monitoring':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'Investigating':
        return 'bg-teal-500/15 text-teal-400 border-teal-500/30';
      case 'Resolved':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-[#111827] border-l border-slate-800 h-full shadow-2xl p-6 overflow-y-auto flex flex-col justify-between text-slate-100">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-5">
            <div className="flex items-center gap-2.5">
              <span className="px-2.5 py-1 rounded-md bg-slate-800 text-teal-400 font-mono text-xs font-bold border border-slate-700">
                {alert.alert_code}
              </span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getStatusBadge(alert.status)}`}>
                {alert.status}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Alert Title */}
          <div className="mb-6">
            <h3 className="text-lg font-bold text-white mb-2 leading-snug">
              {alert.title}
            </h3>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-teal-400" />
                {alert.time_ago}
              </span>
              <span className="flex items-center gap-1">
                <Tag className="w-3.5 h-3.5 text-blue-400" />
                {alert.segment}
              </span>
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-slate-400" />
                {alert.assignee}
              </span>
            </div>
          </div>

          {/* Incident Context */}
          <div className="bg-[#161F30] rounded-xl p-4 border border-slate-800 mb-6 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Incident Context & Scope
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-[#111827] p-3 rounded-lg border border-slate-800">
                <p className="text-slate-400 text-[11px]">Primary Vector</p>
                <p className="font-bold text-white mt-0.5">Micro-burst Anomaly</p>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-slate-800">
                <p className="text-slate-400 text-[11px]">Payment Channel</p>
                <p className="font-bold text-white mt-0.5">{alert.segment}</p>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-slate-800">
                <p className="text-slate-400 text-[11px]">Detection Source</p>
                <p className="font-bold text-teal-400 mt-0.5">Hybrid Engine</p>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-slate-800">
                <p className="text-slate-400 text-[11px]">Assigned Analyst</p>
                <p className="font-bold text-white mt-0.5">{alert.assignee}</p>
              </div>
            </div>
          </div>

          {/* Update Status Actions */}
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-300">Update Alert Status</p>
            <div className="grid grid-cols-3 gap-2">
              {['Monitoring', 'Investigating', 'Resolved'].map((st) => (
                <button
                  key={st}
                  onClick={() => onUpdateStatus(alert.id, st)}
                  className={`py-2 rounded-lg text-xs font-bold border transition-all ${
                    alert.status === st
                      ? 'bg-teal-600 text-white border-teal-500 shadow-md'
                      : 'bg-[#161F30] text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Close */}
        <div className="pt-6 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
