import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Radio,
  Download,
  AlertTriangle,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const Transactions = () => {
  const { searchQuery, setSearchQuery, liveTransactions, wsConnected } = useFilter();

  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [decisionFilter, setDecisionFilter] = useState('All');
  const [segmentFilter, setSegmentFilter] = useState('All');
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      let url = `http://localhost:8000/api/transactions?page=${page}&limit=${limit}`;
      if (decisionFilter !== 'All') url += `&decision=${encodeURIComponent(decisionFilter)}`;
      if (segmentFilter !== 'All') url += `&segment=${encodeURIComponent(segmentFilter)}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();
      setTransactions(data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page, decisionFilter, segmentFilter, searchQuery]);

  const handleExportCSV = () => {
    window.open('http://localhost:8000/api/export?type=csv', '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Live WebSocket Ticker Stream Banner */}
      <div className="bg-slate-900 text-white p-4 rounded-[16px] shadow-xl border border-slate-800 flex items-center justify-between gap-4 overflow-hidden">
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></div>
          <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
            <Radio className="w-4 h-4" /> Live WebSocket Feed
          </span>
        </div>

        <div className="flex-1 overflow-x-auto whitespace-nowrap scrollbar-none py-1 px-4">
          <div className="flex items-center gap-4 text-xs">
            {liveTransactions.length === 0 ? (
              <span className="text-slate-400 font-medium">
                Listening for live transactions (streaming every 3s)...
              </span>
            ) : (
              liveTransactions.slice(0, 5).map((t, idx) => (
                <div
                  key={t.transaction_id + idx}
                  className="inline-flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700/60 text-slate-200"
                >
                  <span className="font-mono text-slate-400 font-bold">{t.transaction_id}</span>
                  <span className="font-bold text-white">${t.amount}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      t.decision === 'Block'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : t.decision === 'Manual Review'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    }`}
                  >
                    {t.decision} ({t.risk_score})
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <button
          onClick={handleExportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl text-xs font-bold transition-all shrink-0"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Main Table Card */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        {/* Filter Controls Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Transaction Telemetry</h2>
              <p className="text-xs text-slate-500">Real-time scored ledger across micro-channels</p>
            </div>
          </div>

          <div className="flex items-center flex-wrap gap-3">
            {/* Search Input */}
            <div className="relative min-w-[200px]">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search Txn ID, Card, Merchant..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              />
            </div>

            {/* Decision Filter */}
            <select
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
            >
              <option value="All">All Decisions</option>
              <option value="Allow">Allow</option>
              <option value="Manual Review">Manual Review</option>
              <option value="Block">Block</option>
            </select>

            {/* Segment Filter */}
            <select
              value={segmentFilter}
              onChange={(e) => {
                setSegmentFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
            >
              <option value="All">All Segments</option>
              <option value="EU Payments">EU Payments</option>
              <option value="APAC Cards">APAC Cards</option>
              <option value="AU Cards">AU Cards</option>
              <option value="ME Cards">ME Cards</option>
              <option value="AS Cards">AS Cards</option>
            </select>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-200/80">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#E5E9F2] text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-gray-200">
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Card ID</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4">Merchant & Cat</th>
                <th className="py-3 px-4">Country / Billing</th>
                <th className="py-3 px-4 text-center">Risk Score</th>
                <th className="py-3 px-4">Decision</th>
                <th className="py-3 px-4">Top Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-700 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    Loading transactions...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    No transactions match current filters.
                  </td>
                </tr>
              ) : (
                transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {t.transaction_id}
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px] font-mono">
                      {t.timestamp}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-800">{t.card_id}</td>
                    <td className="py-3 px-4 text-right font-extrabold text-slate-900">
                      ${t.amount.toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-bold text-slate-800">{t.merchant_id}</p>
                        <p className="text-[10px] text-slate-400 capitalize">{t.merchant_category}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-800">{t.country}</span>
                        {t.country !== t.billing_country && (
                          <span className="text-[10px] text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200 font-bold">
                            vs {t.billing_country}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-block font-mono font-bold px-2 py-0.5 rounded text-xs ${
                          t.risk_score > 70
                            ? 'bg-rose-100 text-rose-700'
                            : t.risk_score > 40
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {t.risk_score}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-[11px] font-bold border ${
                          t.decision === 'Block'
                            ? 'bg-rose-50 text-rose-600 border-rose-200'
                            : t.decision === 'Manual Review'
                            ? 'bg-amber-50 text-amber-600 border-amber-200'
                            : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                        }`}
                      >
                        {t.decision}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px] truncate max-w-[200px]">
                      {t.reasons && t.reasons.length > 0 ? t.reasons[0] : 'Standard'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="flex items-center justify-between pt-4 mt-2">
          <p className="text-xs text-slate-500">
            Showing Page <strong>{page}</strong> ({transactions.length} records)
          </p>

          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="p-2 border border-gray-200 rounded-xl hover:bg-gray-100 disabled:opacity-40 disabled:hover:bg-transparent transition-colors text-slate-600"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold text-slate-800 px-3 py-1.5 bg-gray-100 rounded-xl">
              {page}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              className="p-2 border border-gray-200 rounded-xl hover:bg-gray-100 transition-colors text-slate-600"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
