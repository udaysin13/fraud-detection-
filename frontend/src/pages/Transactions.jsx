import React, { useState, useEffect, useCallback } from 'react';
import {
  CreditCard,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Radio,
  Download,
  AlertTriangle,
  RefreshCw,
  Eye,
  SlidersHorizontal,
  ArrowUpDown,
  Smartphone,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { BackendErrorBanner } from '../components/BackendErrorBanner';
import {
  formatINR,
  formatTimestamp,
  getRiskStyle,
  getChannelLabel,
} from '../utils/formatters';

export const Transactions = () => {
  const {
    searchQuery,
    setSearchQuery,
    selectedChannel,
    setSelectedChannel,
    liveTransactions,
    wsStatus,
    setSelectedTransactionId,
  } = useFilter();

  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exportError, setExportError] = useState(null);
  const [exporting, setExporting] = useState(false);

  // Filters
  const [decisionFilter, setDecisionFilter] = useState('All');
  const [riskCategoryFilter, setRiskCategoryFilter] = useState('All');
  const [channelFilter, setChannelFilter] = useState(selectedChannel || 'All');
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'amount_desc' | 'risk_desc'

  // Pagination
  const [page, setPage] = useState(1);
  const limit = 25;

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getTransactions({
        page,
        limit,
        decision: decisionFilter,
        risk_category: riskCategoryFilter,
        channel: channelFilter,
        search: searchQuery,
      });

      setTransactions(data || []);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
      setError(err.message || 'Unable to retrieve transaction records.');
    } finally {
      setLoading(false);
    }
  }, [page, decisionFilter, riskCategoryFilter, channelFilter, searchQuery]);

  // Keep the page-level channel filter synchronized with the global header filter.
  // Without this, changing the header to "All Channels" can leave this page filtering
  // by the previously selected channel because useState only reads its initial value.
  useEffect(() => {
    setChannelFilter(selectedChannel || 'All');
    setPage(1);
  }, [selectedChannel]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const handleExportCSV = async () => {
    setExportError(null);
    setExporting(true);
    try {
      const blob = await apiClient.downloadExportCSV();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `vaultguard-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Failed to export transactions:', err);
      setExportError(err.message || 'CSV export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  // Client-side sorting for current page
  const sortedTransactions = [...transactions].sort((a, b) => {
    if (sortBy === 'amount_desc') {
      const amtA = a.amount_inr ?? a.amount ?? 0;
      const amtB = b.amount_inr ?? b.amount ?? 0;
      return amtB - amtA;
    }
    if (sortBy === 'risk_desc') {
      return (b.risk_score || 0) - (a.risk_score || 0);
    }
    // Default newest
    return (b.id || 0) - (a.id || 0);
  });

  return (
    <div className="space-y-5">
      {/* Live WebSocket Simulated Stream Ticker Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-card-soft flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-pulse"></div>
          <span className="font-extrabold uppercase tracking-wider text-teal-600 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5" />
            Live Stream Feed (Simulated)
          </span>
          <span className="text-[10px] text-slate-500 hidden sm:inline">
            Status: {wsStatus}
          </span>
        </div>

        <div className="flex-1 min-w-0 overflow-x-auto whitespace-nowrap scrollbar-none py-0.5">
          <div className="flex items-center gap-2.5 text-xs">
            {liveTransactions.length === 0 ? (
              <span className="text-slate-500 italic">
                Awaiting incoming stream transactions...
              </span>
            ) : (
              liveTransactions.slice(0, 4).map((t, idx) => {
                const style = getRiskStyle(t.decision, t.risk_score);
                return (
                  <button
                    key={t.transaction_id + idx}
                    onClick={() => setSelectedTransactionId(t.transaction_id)}
                    className="inline-flex items-center gap-2 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200 text-slate-700 hover:border-slate-300 transition-colors"
                  >
                    <span className="font-mono text-teal-600 font-bold">{t.transaction_id}</span>
                    <span className="font-bold text-slate-800">{formatINR(t.amount_inr ?? t.amount)}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold border ${style.bg} ${style.border} ${style.text}`}>
                      {t.decision} ({t.risk_score})
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleExportCSV}
          disabled={exporting}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-60 disabled:cursor-wait text-slate-800 rounded-lg text-xs font-bold transition-all shrink-0 shadow-sm"
        >
          <Download className="w-3.5 h-3.5" />
          <span>{exporting ? 'Exporting...' : 'Export CSV'}</span>
        </button>
      </div>

      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={fetchTransactions}
          isRetrying={loading}
        />
      )}

      {exportError && (
        <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <div className="flex items-center justify-between gap-3">
            <span>{exportError}</span>
            <button type="button" onClick={() => setExportError(null)} className="font-bold underline">
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Main Transactions Explorer Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
        {/* Controls Toolbar: Search & Multi-Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200">
          {/* Search */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by ID, sender, beneficiary..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />
          </div>

          {/* Filter Dropdowns */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            {/* Channel Filter */}
            <select
              value={channelFilter}
              onChange={(e) => {
                setChannelFilter(e.target.value);
                setSelectedChannel(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="All">All Channels</option>
              <option value="UPI_P2P">UPI P2P</option>
              <option value="UPI_P2M_QR">UPI P2M QR</option>
              <option value="WALLET">Digital Wallet</option>
              <option value="IMPS">IMPS</option>
              <option value="RUPAY_CARD">RuPay Card</option>
            </select>

            {/* Decision Filter */}
            <select
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="All">All Decisions</option>
              <option value="Allow">Allow (Low Risk)</option>
              <option value="Manual Review">Manual Review</option>
              <option value="Block">Block (High Risk)</option>
            </select>

            {/* Risk Category Filter */}
            <select
              value={riskCategoryFilter}
              onChange={(e) => {
                setRiskCategoryFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="All">All Risk Tiers</option>
              <option value="LOW_RISK">Low Risk (0 - 40)</option>
              <option value="REVIEW">Review (41 - 70)</option>
              <option value="HIGH_RISK">High Risk (71 - 100)</option>
            </select>

            {/* Sort Filter */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="newest">Sort: Newest First</option>
              <option value="amount_desc">Sort: Highest Amount</option>
              <option value="risk_desc">Sort: Highest Risk Score</option>
            </select>

            <button
              onClick={fetchTransactions}
              className="p-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-400 hover:text-slate-800 transition-colors"
              title="Refresh Transactions Table"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-400 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Transaction ID</th>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Channel / Type</th>
                <th className="py-2.5 px-3">Amount</th>
                <th className="py-2.5 px-3">Parties (Sender / Beneficiary)</th>
                <th className="py-2.5 px-3">Risk Assessment</th>
                <th className="py-2.5 px-3">Decision</th>
                <th className="py-2.5 px-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-teal-600 mx-auto mb-2" />
                    <p>Querying verified records from database...</p>
                  </td>
                </tr>
              ) : sortedTransactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    <AlertTriangle className="w-6 h-6 text-slate-600 mx-auto mb-2" />
                    <p>No transactions matching the active filters found.</p>
                  </td>
                </tr>
              ) : (
                sortedTransactions.map((t) => {
                  const style = getRiskStyle(t.decision, t.risk_score);
                  const sender = t.sender_vpa || t.sender_id || t.customer_id || '—';
                  const bene = t.beneficiary_vpa || t.beneficiary_id || t.merchant_id || '—';

                  return (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedTransactionId(t.transaction_id)}
                      className="hover:bg-slate-50 transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-3 font-mono font-bold text-teal-600">
                        {t.transaction_id}
                      </td>
                      <td className="py-3 px-3 text-[11px] text-slate-400 whitespace-nowrap">
                        {formatTimestamp(t.timestamp)}
                      </td>
                      <td className="py-3 px-3 text-[11px]">
                        <span className="font-semibold text-slate-800 block">
                          {getChannelLabel(t.channel)}
                        </span>
                        <span className="text-slate-500">
                          {t.transaction_type || 'Transfer'}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-bold text-slate-800 whitespace-nowrap">
                        {formatINR(t.amount_inr ?? t.amount)}
                      </td>
                      <td className="py-3 px-3 text-[11px] max-w-xs truncate">
                        <span className="text-slate-600 font-mono block truncate" title={sender}>
                          From: {sender}
                        </span>
                        <span className="text-slate-500 font-mono block truncate" title={bene}>
                          To: {bene}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <span className={`font-bold font-mono ${style.text}`}>
                            {t.risk_score}
                          </span>
                          <span className="text-[10px] text-slate-500">/ 100</span>
                        </div>
                        <span className="text-[10px] text-slate-400 block truncate">
                          {t.risk_category || 'LOW_RISK'}
                        </span>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${style.bg} ${style.border} ${style.text}`}>
                          {t.decision}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTransactionId(t.transaction_id);
                          }}
                          className="p-1.5 bg-slate-50 hover:bg-slate-100 text-teal-600 rounded-lg transition-colors border border-slate-200 hover:border-slate-300"
                          title="View Full Transaction Context"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-xs text-slate-400">
          <span>
            Page <strong className="text-slate-800">{page}</strong> (showing up to {limit} records)
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 disabled:opacity-40 text-slate-600 rounded-lg border border-slate-200 transition-colors flex items-center gap-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={transactions.length < limit || loading}
              className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 disabled:opacity-40 text-slate-600 rounded-lg border border-slate-200 transition-colors flex items-center gap-1"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
