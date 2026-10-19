import React, { useState } from 'react';
import { X, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';

export const CreateAlertModal = () => {
  const { isCreateAlertOpen, setIsCreateAlertOpen } = useFilter();
  const [title, setTitle] = useState('');
  const [segment, setSegment] = useState('UPI P2P');
  const [assignee, setAssignee] = useState('Aarav Sharma');
  const [status, setStatus] = useState('Monitoring');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isCreateAlertOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const alertCode = `ALT-IN-${Math.floor(100 + Math.random() * 900)}`;

    try {
      await apiClient.createAlert({
        alert_code: alertCode,
        title,
        segment,
        time_ago: 'Just now',
        status,
        assignee,
      });

      setIsCreateAlertOpen(false);
      setTitle('');
    } catch (err) {
      setError(err.message || 'Failed to create security alert');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#111827] rounded-2xl shadow-2xl border border-slate-800 w-full max-w-md p-6 relative animate-in fade-in zoom-in-95 duration-200 text-slate-100">
        <button
          onClick={() => setIsCreateAlertOpen(false)}
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5 border-b border-slate-800 pb-3">
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Create Security Alert</h3>
            <p className="text-xs text-slate-400">Add operational monitoring rule or manual flag</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Alert Title / Anomaly Description
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Unusual micro-velocity detected on QR terminal"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2 bg-[#161F30] border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-teal-500 placeholder-slate-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Payment Channel
              </label>
              <select
                value={segment}
                onChange={(e) => setSegment(e.target.value)}
                className="w-full px-3 py-2 bg-[#161F30] border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="UPI P2P">UPI P2P</option>
                <option value="UPI P2M QR">UPI P2M QR</option>
                <option value="Digital Wallet">Digital Wallet</option>
                <option value="IMPS">IMPS</option>
                <option value="RuPay Card">RuPay Card</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Assigned Analyst
              </label>
              <select
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                className="w-full px-3 py-2 bg-[#161F30] border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-teal-500"
              >
                <option value="Aarav Sharma">Aarav Sharma</option>
                <option value="Priya Nair">Priya Nair</option>
                <option value="Rohan Verma">Rohan Verma</option>
                <option value="Sneha Patel">Sneha Patel</option>
                <option value="Risk Engine">Risk Engine</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Initial Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-2 bg-[#161F30] border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="Monitoring">Monitoring</option>
              <option value="Investigating">Investigating</option>
              <option value="Pending Review">Pending Review</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsCreateAlertOpen(false)}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white shadow-md transition-all disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
