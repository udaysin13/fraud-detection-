import React from 'react';
import { FileBarChart, Download, FileText, Calendar, CheckCircle2 } from 'lucide-react';

export const Reports = () => {
  const handleExportCSV = () => {
    window.open('http://localhost:8000/api/export?type=csv', '_blank');
  };

  const reportLogs = [
    {
      id: 'REP-2026-09',
      name: 'VaultGuard Monthly Micro-Fraud Telemetry Report',
      date: '2026-09-23',
      records: '55,000 txns',
      status: 'Ready',
    },
    {
      id: 'REP-2026-08',
      name: 'Card Testing & Velocity Pattern Audit Trail',
      date: '2026-09-15',
      records: '12,400 txns',
      status: 'Ready',
    },
    {
      id: 'REP-2026-07',
      name: 'Structuring Threshold Compliance Report ($10k SAR)',
      date: '2026-09-01',
      records: '4,890 txns',
      status: 'Ready',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#14B8A6]/10 text-[#14B8A6] rounded-xl">
            <FileBarChart className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Fraud Telemetry & Reports</h2>
            <p className="text-xs text-slate-500">Scheduled exports, loss prevention analytics, and audit logs</p>
          </div>
        </div>

        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl text-xs font-bold shadow-md transition-all active:scale-95"
        >
          <Download className="w-4 h-4" />
          <span>Export Scored CSV (55k Records)</span>
        </button>
      </div>

      {/* Report Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Scored Records</p>
          <p className="text-3xl font-extrabold text-slate-900 mt-2">55,000</p>
          <p className="text-xs text-slate-500 mt-1">Full historical transaction dataset</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Micro-Fraud Incidents</p>
          <p className="text-3xl font-extrabold text-[#F97316] mt-2">1,100</p>
          <p className="text-xs text-slate-500 mt-1">2.00% overall fraud prevalence</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Prevented Losses Est.</p>
          <p className="text-3xl font-extrabold text-emerald-600 mt-2">$42,890.00</p>
          <p className="text-xs text-slate-500 mt-1">Automated block decision savings</p>
        </div>
      </div>

      {/* Reports List */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <h3 className="text-base font-bold text-slate-900 mb-4">Available Audit Reports</h3>

        <div className="space-y-3">
          {reportLogs.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200/80 rounded-2xl hover:bg-slate-100/70 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-200 text-slate-700 rounded-xl">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900">{r.name}</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    ID: <span className="font-mono">{r.id}</span> | Generated: {r.date} | Scope: {r.records}
                  </p>
                </div>
              </div>

              <button
                onClick={handleExportCSV}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white hover:bg-slate-800 rounded-xl text-xs font-bold transition-all"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
