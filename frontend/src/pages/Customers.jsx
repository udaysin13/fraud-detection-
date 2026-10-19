import React, { useState, useEffect, useCallback } from 'react';
import { Users, Search, ChevronLeft, ChevronRight, ShieldAlert, RefreshCw } from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { BackendErrorBanner } from '../components/BackendErrorBanner';
import { formatINR, formatIndianNumber } from '../utils/formatters';

export const Customers = () => {
  const { searchQuery, setSearchQuery } = useFilter();

  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [riskFilter, setRiskFilter] = useState('All');
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCustomers({
        page,
        limit,
        risk_level: riskFilter,
        search: searchQuery,
      });
      setCustomers(data || []);
    } catch (err) {
      console.error('Failed to fetch customers:', err);
      setError(err.message || 'Unable to retrieve customer risk profiles.');
    } finally {
      setLoading(false);
    }
  }, [page, riskFilter, searchQuery]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-600 rounded-xl">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Customer Risk Profiles</h2>
            <p className="text-xs text-slate-400">
              Account-level behavior, cumulative Indian Rupee spend, and fraud incidents
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
          >
            <option value="All">All Risk Tiers</option>
            <option value="Low">Low Risk Tier</option>
            <option value="Medium">Medium Risk Tier</option>
            <option value="High">High Risk Tier</option>
          </select>

          <button
            onClick={fetchCustomers}
            className="p-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-400 hover:text-slate-800 transition-colors"
            title="Refresh Customers"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={fetchCustomers}
          isRetrying={loading}
        />
      )}

      {/* Main Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search customer ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-400 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Customer ID</th>
                <th className="py-2.5 px-3">Payment Segment</th>
                <th className="py-2.5 px-3">Total Transactions</th>
                <th className="py-2.5 px-3">Cumulative Volume</th>
                <th className="py-2.5 px-3">Incidents Flagged</th>
                <th className="py-2.5 px-3">Risk Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-teal-600 mx-auto mb-2" />
                    <p>Loading customer accounts...</p>
                  </td>
                </tr>
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 italic">
                    No customer accounts found.
                  </td>
                </tr>
              ) : (
                customers.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-teal-600">
                      {c.customer_id}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-400">
                      {c.segment}
                    </td>
                    <td className="py-3 px-3 font-bold text-slate-800">
                      {formatIndianNumber(c.total_transactions)}
                    </td>
                    <td className="py-3 px-3 font-mono font-bold text-slate-700">
                      {formatINR(c.total_spend)}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`font-mono font-bold ${c.fraud_incidents > 0 ? 'text-rose-500' : 'text-slate-500'}`}>
                        {c.fraud_incidents}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        c.risk_level === 'High'
                          ? 'bg-rose-50 text-rose-500 border-rose-200'
                          : c.risk_level === 'Medium'
                          ? 'bg-amber-50 text-amber-600 border-amber-200'
                          : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                      }`}>
                        {c.risk_level}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-200 text-xs text-slate-400">
          <span>Page {page}</span>
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
              disabled={customers.length < limit || loading}
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
