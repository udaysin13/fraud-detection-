import React from 'react';
import { X, ShieldCheck, Info, AlertTriangle, Database, Cpu } from 'lucide-react';

export const AboutModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-[#111827] border border-slate-800 rounded-2xl max-w-xl w-full p-6 text-slate-200 shadow-2xl relative space-y-5">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Title */}
        <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
          <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-extrabold text-white">VaultGuard Architecture & Scope</h3>
            <p className="text-xs text-slate-400">Indian Digital Payment Fraud Detection in Small Transactions</p>
          </div>
        </div>

        {/* Scope and Architecture */}
        <div className="space-y-3.5 text-xs text-slate-300 leading-relaxed">
          <div className="p-3.5 rounded-xl bg-[#161F30] border border-slate-800 space-y-1.5">
            <h4 className="font-bold text-white flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-teal-400" />
              Dual Hybrid ML Engine (Supervised + Unsupervised)
            </h4>
            <p className="text-slate-400">
              VaultGuard utilizes an ensemble combining class-weighted <strong>XGBoost (150 trees)</strong> for known micro-attack patterns and <strong>Isolation Forest</strong> for novel zero-day anomaly detection, explained in real-time via <strong>TreeSHAP attributions</strong>.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#161F30] border border-slate-800 space-y-1.5">
            <h4 className="font-bold text-white flex items-center gap-1.5">
              <Database className="w-4 h-4 text-blue-400" />
              Focus on Indian Digital Payments
            </h4>
            <p className="text-slate-400">
              The detection models are explicitly tailored for low-value Indian payment flows: UPI P2P transfers, UPI P2M QR merchant checkouts, digital wallets, IMPS, and RuPay card networks, focusing on micro-testing attacks, rapid velocity bursts, SIM-swap account takeovers, and amount structuring.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 space-y-1.5">
            <h4 className="font-bold flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              System Limitations & Academic Disclosures
            </h4>
            <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-200/90">
              <li>
                <strong>Synthetic Evaluation Dataset</strong>: The ~55,000 transaction dataset is a statistically representative synthetic model developed for evaluation and research, not live proprietary bank or NPCI production records.
              </li>
              <li>
                <strong>Decision Support Only</strong>: Risk scores and decisions (Allow, Manual Review, Block) represent probabilistic risk assessments and do not guarantee transactional safety or legally prove fraudulent conduct.
              </li>
              <li>
                <strong>Simulated Live Stream</strong>: The WebSocket stream periodically generates synthetic scenarios to demonstrate real-time scoring latency.
              </li>
            </ul>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition-colors shadow-md"
          >
            Understood
          </button>
        </div>
      </div>
    </div>
  );
};
