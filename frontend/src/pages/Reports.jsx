import React, { useState, useEffect } from 'react';
import { FileBarChart, Download, Database } from 'lucide-react';
import { apiClient } from '../api/client';
import { formatIndianNumber } from '../utils/formatters';

export const Reports = () => {
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiClient
      .getAnalyticsOverview()
      .then((data) => setOverview(data))
      .catch((err) => setError(err.message || 'Unable to load analytics.'));
  }, []);

  const handleExportCSV = () => {
    window.open(apiClient.getExportUrl(), '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-600 rounded-xl">
            <FileBarChart className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Fraud Telemetry & Audit Reports</h2>
            <p className="text-xs text-slate-500">Export the transaction records currently available in the database.</p>
          </div>
        </div>

        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-slate-800 rounded-lg text-xs font-bold shadow-md transition-all active:scale-95"
        >
          <Download className="w-4 h-4" />
          <span>Export transaction CSV</span>
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-card-soft space-y-3">
        <h3 className="text-sm font-bold text-slate-800">Current database summary</h3>
        {error ? (
          <p role="alert" className="text-sm text-rose-700">{error}</p>
        ) : (
          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div><dt className="text-slate-500">Transaction records</dt><dd className="mt-1 font-semibold text-slate-800">{overview ? formatIndianNumber(overview.total_transactions) : 'Loading...'}</dd></div>
            <div><dt className="text-slate-500">Dataset fraud labels</dt><dd className="mt-1 font-semibold text-slate-800">{overview ? formatIndianNumber(overview.dataset_fraud_labels) : 'Loading...'}</dd></div>
            <div><dt className="text-slate-500">Risk score above 40</dt><dd className="mt-1 font-semibold text-slate-800">{overview ? formatIndianNumber(overview.total_fraud_flagged) : 'Loading...'}</dd></div>
          </dl>
        )}
        <p className="flex items-start gap-2 border-t border-slate-200 pt-3 text-xs text-slate-500">
          <Database className="h-4 w-4 shrink-0 text-blue-700" aria-hidden="true" />
          These are database counts, not generated audit reports or estimates of prevented loss. The CSV export is the implemented report action.
        </p>
      </div>
    </div>
  );
};
