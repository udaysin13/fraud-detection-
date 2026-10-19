import React from 'react';
import { CheckSquare, Info } from 'lucide-react';

export const Compliance = () => {
  const requirements = [
    {
      title: 'PMLA & FIU-IND Structuring Detection (₹50k / ₹10k Thresholds)',
      status: 'Not assessed',
      detail: 'The prototype includes transaction amount and velocity features; it does not establish regulatory compliance.',
    },
    {
      title: 'NPCI UPI Security Directive & SIM-Binding Integrity',
      status: 'Not assessed',
      detail: 'SIM-change and new-device signals are available to the model. No external directive validation is performed.',
    },
    {
      title: 'RBI Master Directions on Digital Payment Security Controls',
      status: 'Not assessed',
      detail: 'The model uses point-in-time transaction features for this academic demonstration; controls have not been independently audited.',
    },
    {
      title: 'CERT-In Cyber Incident Reporting & Audit Trail',
      status: 'Not assessed',
      detail: 'This project does not claim immutable logging or compliance with incident-reporting requirements.',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-600 rounded-xl">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Regulatory Compliance & AML Standards</h2>
            <p className="text-xs text-slate-500">Educational mapping only. This page is not a compliance certification or legal assessment.</p>
          </div>
        </div>

        <span className="px-3.5 py-1.5 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-xs font-bold flex items-center gap-1.5">
          <Info className="w-4 h-4" />
          <span>Compliance not assessed</span>
        </span>
      </div>

      {/* Informational mapping only */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
        <h3 className="text-sm font-bold text-slate-800">Indian Digital Payment Regulatory Framework</h3>
        <div className="space-y-3">
          {requirements.map((req, idx) => (
            <div
              key={idx}
              className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-wrap items-center justify-between gap-3 hover:border-slate-300 transition-colors"
            >
              <div className="space-y-1 max-w-xl">
                <h4 className="text-xs font-bold text-slate-800">{req.title}</h4>
                <p className="text-[11px] text-slate-400">{req.detail}</p>
              </div>

              <span className="px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-[11px] font-bold shrink-0">
                {req.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
