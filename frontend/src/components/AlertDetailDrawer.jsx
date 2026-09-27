import React from 'react';
import { X, ShieldAlert, Clock, User, Tag, CheckCircle2, RefreshCw } from 'lucide-react';

export const AlertDetailDrawer = ({ alert, onClose, onUpdateStatus }) => {
  if (!alert) return null;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Monitoring':
        return 'bg-orange-50 text-[#F97316] border-orange-200';
      case 'Investigating':
        return 'bg-teal-50 text-[#14B8A6] border-teal-200';
      case 'Resolved':
        return 'bg-slate-100 text-slate-800 border-slate-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl p-6 overflow-y-auto flex flex-col justify-between border-l border-gray-200">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-100 pb-4 mb-5">
            <div className="flex items-center gap-2.5">
              <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono text-xs font-bold">
                {alert.alert_code}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusBadge(
                  alert.status
                )}`}
              >
                {alert.status}
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-slate-800 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Alert Title */}
          <div className="mb-6">
            <h3 className="text-xl font-extrabold text-slate-900 mb-2 leading-snug">
              {alert.title}
            </h3>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-orange-500" />
                {alert.time_ago}
              </span>
              <span className="flex items-center gap-1">
                <Tag className="w-3.5 h-3.5 text-teal-500" />
                {alert.segment}
              </span>
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-slate-400" />
                {alert.assignee}
              </span>
            </div>
          </div>

          {/* Context Details */}
          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200/80 mb-6 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Incident Context & Signals
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-slate-200/60 shadow-sm">
                <p className="text-slate-400 font-medium text-[11px]">Primary Vector</p>
                <p className="font-bold text-slate-800 mt-0.5">Micro-burst Velocity</p>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200/60 shadow-sm">
                <p className="text-slate-400 font-medium text-[11px]">Affected Segment</p>
                <p className="font-bold text-slate-800 mt-0.5">{alert.segment}</p>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200/60 shadow-sm">
                <p className="text-slate-400 font-medium text-[11px]">Risk Level</p>
                <p className="font-bold text-orange-600 mt-0.5">High Priority</p>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200/60 shadow-sm">
                <p className="text-slate-400 font-medium text-[11px]">Assigned Owner</p>
                <p className="font-bold text-slate-800 mt-0.5">{alert.assignee}</p>
              </div>
            </div>
          </div>

          {/* Update Status Actions */}
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-700">Update Alert Status</p>
            <div className="grid grid-cols-3 gap-2">
              {['Monitoring', 'Investigating', 'Resolved'].map((st) => (
                <button
                  key={st}
                  onClick={() => onUpdateStatus(alert.id, st)}
                  className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                    alert.status === st
                      ? 'bg-[#1B212C] text-white border-[#1B212C] shadow-md'
                      : 'bg-white text-slate-700 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Close */}
        <div className="pt-6 border-t border-gray-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 text-slate-700 transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
