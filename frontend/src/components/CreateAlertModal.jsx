import React, { useState } from 'react';
import { X, ShieldAlert } from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const CreateAlertModal = () => {
  const { isCreateAlertOpen, setIsCreateAlertOpen } = useFilter();
  const [title, setTitle] = useState('');
  const [segment, setSegment] = useState('EU Payments');
  const [assignee, setAssignee] = useState('Emily Wang');
  const [status, setStatus] = useState('Monitoring');

  if (!isCreateAlertOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const alertCode = `ALT-${Math.floor(100 + Math.random() * 900)}`;

    fetch('http://localhost:8000/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        alert_code: alertCode,
        title,
        segment,
        time_ago: 'Just now',
        status,
        assignee,
      }),
    })
      .then((res) => res.json())
      .then(() => {
        setIsCreateAlertOpen(false);
        setTitle('');
      })
      .catch((err) => {
        console.error('Failed to create alert:', err);
        setIsCreateAlertOpen(false);
      });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-[20px] shadow-2xl border border-gray-100 w-full max-w-md p-6 relative animate-in fade-in zoom-in-95 duration-200">
        <button
          onClick={() => setIsCreateAlertOpen(false)}
          className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-orange-100 text-[#F97316] flex items-center justify-center">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Create Security Alert</h3>
            <p className="text-xs text-slate-500">Configure new rule or incident monitor</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Alert Description / Title
            </label>
            <input
              type="text"
              required
              placeholder="e.g. High transaction velocity on APAC debit cards"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/30"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Segment
              </label>
              <select
                value={segment}
                onChange={(e) => setSegment(e.target.value)}
                className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              >
                <option value="EU Payments">EU Payments</option>
                <option value="APAC Cards">APAC Cards</option>
                <option value="AU Cards">AU Cards</option>
                <option value="ME Cards">ME Cards</option>
                <option value="AS Cards">AS Cards</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Assignee
              </label>
              <select
                value={assignee}
                onChange={(e) => setAssignee(e.target.value)}
                className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              >
                <option value="Emily Wang">Emily Wang</option>
                <option value="John Lee">John Lee</option>
                <option value="Amina Hassan">Amina Hassan</option>
                <option value="Mike Chen">Mike Chen</option>
                <option value="Sara Lee">Sara Lee</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Initial Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
            >
              <option value="Monitoring">Monitoring</option>
              <option value="Investigating">Investigating</option>
              <option value="Pending Review">Pending Review</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setIsCreateAlertOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-xl text-xs font-bold bg-[#F97316] hover:bg-[#EA580C] text-white shadow-md transition-all"
            >
              Submit Alert
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
