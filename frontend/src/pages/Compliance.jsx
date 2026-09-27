import React from 'react';
import { CheckSquare, ShieldCheck, FileCheck, Lock, AlertCircle } from 'lucide-react';

export const Compliance = () => {
  const requirements = [
    {
      title: 'Structuring & Smurfing Detection ($10k Threshold)',
      status: 'Compliant',
      detail: 'Enforces sub-threshold aggregation tracking across 1-hour to 24-hour windows.',
    },
    {
      title: 'Suspicious Activity Report (SAR) Automated Filings',
      status: 'Compliant',
      detail: 'Auto-generates SAR export packages for block decisions with risk scores >= 85.',
    },
    {
      title: 'PCI-DSS Data Tokenization & Masking',
      status: 'Compliant',
      detail: 'Card PAN numbers are truncated to 6-digit BIN ranges; no raw CVV or PAN stored.',
    },
    {
      title: 'AML Watchlist & OFAC Sanctions Cross-Checking',
      status: 'Compliant',
      detail: 'Country and billing country ISO pairs validated against OFAC high-risk vectors.',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Regulatory Compliance & AML Audit</h2>
            <p className="text-xs text-slate-500">Structuring threshold audits, SAR filings, and PCI-DSS compliance</p>
          </div>
        </div>

        <span className="px-3.5 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold border border-emerald-300 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4" />
          <span>Audit Status: 100% Compliant</span>
        </span>
      </div>

      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <h3 className="text-base font-bold text-slate-900 mb-4">Regulatory Standards Matrix</h3>
        <div className="space-y-3">
          {requirements.map((req, idx) => (
            <div
              key={idx}
              className="p-4 bg-gray-50 border border-gray-200/80 rounded-2xl flex items-center justify-between"
            >
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-slate-900">{req.title}</h4>
                <p className="text-xs text-slate-500">{req.detail}</p>
              </div>

              <span className="px-3 py-1 bg-emerald-50 text-emerald-600 border border-emerald-200 rounded-full text-xs font-bold shrink-0">
                {req.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
