import React, { useEffect, useState } from 'react';
import {
  X,
  ShieldAlert,
  Clock,
  Smartphone,
  CreditCard,
  Building,
  User,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Cpu,
  Layers,
  MapPin,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { formatINR, formatTimestamp, getRiskStyle, getChannelLabel } from '../utils/formatters';

export const TransactionDetailDrawer = ({ transactionId, onClose }) => {
  const [txn, setTxn] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!transactionId) {
      setTxn(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    apiClient
      .getTransactionById(transactionId)
      .then((data) => {
        if (isMounted) setTxn(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message || 'Failed to load transaction details.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [transactionId]);

  if (!transactionId) return null;

  const riskStyle = getRiskStyle(txn?.decision, txn?.risk_score);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-[#111827] border-l border-slate-800 h-full shadow-2xl p-6 overflow-y-auto flex flex-col justify-between text-slate-100">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-5">
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-md bg-slate-800 text-teal-400 border border-slate-700">
                {transactionId}
              </span>
              {txn && (
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${riskStyle.bg} ${riskStyle.border} ${riskStyle.text}`}>
                  {txn.decision} ({txn.risk_score})
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {loading ? (
            <div className="py-24 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-xs text-slate-400">Fetching transaction context from database...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs space-y-2">
              <p className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                Unable to load transaction
              </p>
              <p>{error}</p>
            </div>
          ) : txn ? (
            <div className="space-y-6">
              {/* Top Summary Card */}
              <div className="bg-[#161F30] border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                    Transaction Amount
                  </span>
                  <div className="text-2xl font-extrabold text-white mt-0.5">
                    {formatINR(txn.amount_inr ?? txn.amount)}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {getChannelLabel(txn.channel)} • {txn.transaction_type || 'P2P Transfer'}
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                    Risk Category
                  </span>
                  <div className={`text-sm font-extrabold mt-0.5 ${riskStyle.text}`}>
                    {txn.risk_category || 'LOW_RISK'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Status: <span className="text-slate-200 font-bold">{txn.status}</span>
                  </div>
                </div>
              </div>

              {/* Sender & Beneficiary Section */}
              <div className="bg-[#161F30] border border-slate-800/80 rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <CreditCard className="w-3.5 h-3.5 text-teal-400" />
                  Transfer Parties & Routing
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#111827] p-3 rounded-lg border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Sender Account</span>
                    <p className="font-mono font-bold text-slate-100 truncate">{txn.sender_vpa || txn.sender_id || txn.customer_id || 'Unknown'}</p>
                    <p className="text-[11px] text-slate-400">ID: {txn.sender_id || txn.customer_id || '—'}</p>
                  </div>

                  <div className="bg-[#111827] p-3 rounded-lg border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Beneficiary Account</span>
                    <p className="font-mono font-bold text-slate-100 truncate">{txn.beneficiary_vpa || txn.beneficiary_id || txn.merchant_id || 'Unknown'}</p>
                    <p className="text-[11px] text-slate-400">Category: {txn.merchant_category || 'P2P'}</p>
                  </div>
                </div>
              </div>

              {/* Device & Security Signals */}
              <div className="bg-[#161F30] border border-slate-800/80 rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Smartphone className="w-3.5 h-3.5 text-blue-400" />
                  Device & ATO Risk Indicators
                </h4>

                <div className="grid grid-cols-3 gap-2.5 text-xs text-center">
                  <div className="bg-[#111827] p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block mb-1">New Device?</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${txn.is_new_device ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'}`}>
                      {txn.is_new_device ? 'YES (Flagged)' : 'NO (Verified)'}
                    </span>
                  </div>

                  <div className="bg-[#111827] p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block mb-1">SIM Change</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${txn.sim_change_flag ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-800 text-slate-400'}`}>
                      {txn.sim_change_flag ? 'RECENT SWAP' : 'NORMAL'}
                    </span>
                  </div>

                  <div className="bg-[#111827] p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-400 block mb-1">Location</span>
                    <span className="text-slate-200 font-bold block truncate">
                      {txn.ip_location_state || 'India'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Evidence-Based Explanations */}
              <div className="bg-[#161F30] border border-slate-800/80 rounded-xl p-4 space-y-2.5">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-teal-400" />
                  ML Risk Attribution & Evidence Signals
                </h4>

                <ul className="space-y-1.5 text-xs">
                  {Array.isArray(txn.reasons) && txn.reasons.length > 0 ? (
                    txn.reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 bg-[#111827] p-2.5 rounded-lg border border-slate-800/60 text-slate-300">
                        <span className="w-4 h-4 rounded-full bg-slate-800 text-teal-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <span>{r}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-slate-400 italic">No anomaly reasons recorded.</li>
                  )}
                </ul>
              </div>

              {/* Audit Metadata */}
              <div className="text-[11px] text-slate-500 space-y-1 pt-2 border-t border-slate-800">
                <p>Scored At: {formatTimestamp(txn.scored_at || txn.timestamp)}</p>
                <p>Model Engine: {txn.model_version || 'v1.0.0-xgb-iso-hybrid'}</p>
                <p>Source Record: {txn.source || 'persisted_db'}</p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-bold transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
};
