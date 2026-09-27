import React, { useState, useEffect } from 'react';
import { FileSearch, Search, UserCheck, ShieldAlert, Plus, MessageSquare } from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const Investigations = () => {
  const { searchQuery, setSearchQuery } = useFilter();

  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [activeCaseNotes, setActiveCaseNotes] = useState(null);

  const fetchCases = async () => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/api/cases?limit=50';
      if (statusFilter !== 'All') url += `&status=${encodeURIComponent(statusFilter)}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();
      setCases(data);
    } catch (err) {
      console.error('Failed to fetch cases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [statusFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-50 text-amber-600 rounded-xl">
            <FileSearch className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Fraud Investigation Roster</h2>
            <p className="text-xs text-slate-500">Active analyst cases and high-priority account reviews</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-slate-700"
          >
            <option value="All">All Case Statuses</option>
            <option value="Open">Open</option>
            <option value="In Review">In Review</option>
            <option value="Resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Grid of Cases */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 text-xs bg-white rounded-[16px] border border-gray-200">
          Loading investigation cases...
        </div>
      ) : cases.length === 0 ? (
        <div className="p-12 text-center text-slate-400 text-xs bg-white rounded-[16px] border border-gray-200">
          No investigation cases found.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {cases.map((c) => (
            <div
              key={c.id}
              className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft hover:shadow-card-hover transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xs font-bold bg-[#1B212C] text-white px-2.5 py-1 rounded-lg">
                    {c.case_id}
                  </span>
                  <span
                    className={`px-3 py-1 rounded-full text-[11px] font-bold border ${
                      c.status === 'Open'
                        ? 'bg-rose-50 text-rose-600 border-rose-200'
                        : c.status === 'In Review'
                        ? 'bg-amber-50 text-amber-600 border-amber-200'
                        : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                    }`}
                  >
                    {c.status}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-900 mb-1 leading-snug">
                  {c.title}
                </h4>
                <p className="text-xs text-slate-500 font-mono mb-4">
                  Customer: <strong>{c.customer_id}</strong>
                </p>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60 mb-4 flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Risk Score:</span>
                  <span className="font-mono font-extrabold text-rose-600">
                    {c.risk_score} / 100
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium flex items-center gap-1">
                  <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                  {c.assigned_analyst}
                </span>

                <button
                  onClick={() => setActiveCaseNotes(c)}
                  className="text-xs font-bold text-[#F97316] hover:underline flex items-center gap-1"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Notes</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Interactive Case Note Dialog */}
      {activeCaseNotes && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-[20px] shadow-2xl border border-gray-100 w-full max-w-md p-6">
            <h3 className="text-base font-bold text-slate-900 mb-1">
              Case Notes: {activeCaseNotes.case_id}
            </h3>
            <p className="text-xs text-slate-500 mb-4">{activeCaseNotes.title}</p>
            <textarea
              rows={4}
              placeholder="Enter analyst observations, card block verification, or SAR filing notes..."
              className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-500/30 mb-4"
            ></textarea>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setActiveCaseNotes(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-gray-100"
              >
                Close
              </button>
              <button
                onClick={() => {
                  alert('Case notes saved successfully.');
                  setActiveCaseNotes(null);
                }}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#F97316] text-white shadow-md"
              >
                Save Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
