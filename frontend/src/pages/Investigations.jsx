import React, { useState, useEffect, useCallback } from 'react';
import {
  FileSearch,
  Search,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { BackendErrorBanner } from '../components/BackendErrorBanner';
import { getRiskStyle } from '../utils/formatters';

const CASE_ACTIONS = [
  { label: 'Review', status: 'Under Review' },
  { label: 'Escalate', status: 'Escalated' },
  { label: 'False positive', status: 'False Positive' },
  { label: 'Confirm fraud', status: 'Confirmed Fraud' },
];

const normalizeStatus = (status) =>
  String(status || '').trim().replaceAll('_', ' ').replace(/\s+/g, ' ').toLowerCase();

const displayStatus = (status) =>
  normalizeStatus(status).replace(/\b\w/g, (letter) => letter.toUpperCase());

const StatusActions = ({ item, kind, onUpdate, onCreateCase, busy }) => (
  <div className="flex flex-wrap justify-end gap-1.5">
    {kind === 'alert' && <button type="button" disabled={busy} onClick={() => onCreateCase(item)} className="rounded border border-blue-200 bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-700 hover:border-blue-500 disabled:opacity-50">Open case</button>}
    {CASE_ACTIONS.map((action) => (
      <button
        key={action.status}
        type="button"
        disabled={busy}
        onClick={() => onUpdate(kind, item, action.status)}
        className="rounded border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-700 hover:border-teal-600 hover:text-teal-800 disabled:cursor-wait disabled:opacity-50"
      >
        {action.label}
      </button>
    ))}
  </div>
);

export const Investigations = () => {
  const { searchQuery, setSearchQuery } = useFilter();

  const [cases, setCases] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('All');
  const [savingId, setSavingId] = useState(null);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getActiveCaseQueue({
        limit: 50,
        search: searchQuery,
      });
      setCases(data?.cases || []);
      setAlerts(data?.alerts || []);
    } catch (err) {
      console.error('Failed to fetch cases:', err);
      setError(err.message || 'Unable to retrieve investigation cases.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleStatusUpdate = async (kind, item, nextStatus) => {
    const rowId = kind === 'case' ? `case:${item.case_id}` : `alert:${item.id}`;
    setSavingId(rowId);
    setError(null);
    try {
      if (kind === 'case') {
        await apiClient.updateCaseStatus(item.case_id, nextStatus);
      } else {
        await apiClient.updateFraudAlertStatus(item.id, nextStatus);
      }
      await fetchCases();
    } catch (err) {
      setError(err.message || 'Unable to update case status.');
    } finally {
      setSavingId(null);
    }
  };

  const handleCreateCase = async (alert) => {
    setSavingId(`alert:${alert.id}`);
    setError(null);
    try {
      await apiClient.createCase({
        transaction_id: alert.transaction_id,
        severity: alert.risk_category === 'HIGH_RISK' ? 'HIGH' : 'MEDIUM',
      });
      await fetchCases();
    } catch (err) {
      setError(err.message || 'Unable to create an investigation case.');
    } finally {
      setSavingId(null);
    }
  };

  const matchesStatus = (status) => {
    if (statusFilter === 'All') return true;
    const normalized = normalizeStatus(status);
    const selected = normalizeStatus(statusFilter);
    return normalized === selected || (selected === 'under review' && normalized === 'in review');
  };
  const visibleCases = cases.filter((item) => matchesStatus(item.status));
  const visibleAlerts = alerts.filter((item) => matchesStatus(item.status));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-600 rounded-xl">
            <FileSearch className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Analyst Case Management</h2>
            <p className="text-xs text-slate-400">
              Review persisted cases and fraud alerts; status changes are saved to the database.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold focus:outline-none focus:border-teal-500"
          >
            <option value="All">All active statuses</option>
            <option value="Open">Open</option>
            <option value="Under Review">Under review</option>
            <option value="Escalated">Escalated</option>
          </select>

          <button
            onClick={fetchCases}
            className="p-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-400 hover:text-slate-800 transition-colors"
            title="Refresh Cases"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={fetchCases}
          isRetrying={loading}
        />
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-card-soft">
          <p className="text-xs text-slate-500">Active cases</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{cases.length}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-card-soft">
          <p className="text-xs text-slate-500">Active fraud alerts</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{alerts.length}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-card-soft">
          <p className="text-xs text-slate-500">High-risk alerts</p>
          <p className="mt-1 text-2xl font-bold text-rose-700">{alerts.filter((item) => item.risk_score > 70).length}</p>
        </div>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-card-soft sm:p-5" aria-labelledby="active-alerts-title">
        <div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-3">
          <ShieldAlert className="h-4 w-4 text-rose-700" aria-hidden="true" />
          <div>
            <h3 id="active-alerts-title" className="text-sm font-bold text-slate-800">Flagged transactions and fraud alerts</h3>
            <p className="text-xs text-slate-500">Persistent alerts linked to transaction records; simulated stream events are excluded.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-xs text-slate-600">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Alert / Transaction</th>
                <th className="px-3 py-2.5">Payment</th>
                <th className="px-3 py-2.5">Risk</th>
                <th className="px-3 py-2.5">Reason</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5 text-right">Analyst actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr><td colSpan={6} className="py-10 text-center text-slate-500"><RefreshCw className="mx-auto mb-2 h-5 w-5 animate-spin text-teal-700" />Loading active alerts...</td></tr>
              ) : visibleAlerts.length === 0 ? (
                <tr><td colSpan={6} className="py-10 text-center text-slate-500">No active fraud alerts match this filter.</td></tr>
              ) : visibleAlerts.map((alert) => {
                const style = getRiskStyle('', alert.risk_score);
                const busy = savingId === `alert:${alert.id}`;
                return (
                  <tr key={alert.id}>
                    <td className="px-3 py-3">
                      <span className="block font-mono font-semibold text-teal-800">{alert.alert_id}</span>
                      <span className="mt-1 block font-mono text-[11px] text-slate-500">{alert.transaction_id}</span>
                      {alert.timestamp && <span className="mt-1 block text-[10px] text-slate-400">{alert.timestamp}</span>}
                    </td>
                    <td className="px-3 py-3">{alert.channel || 'Unavailable'}<span className="block mt-1">{alert.amount_inr != null ? `₹${Number(alert.amount_inr).toLocaleString('en-IN')}` : 'Amount unavailable'}</span></td>
                    <td className="px-3 py-3"><span className={`rounded border px-2 py-1 font-semibold ${style.bg} ${style.border} ${style.text}`}>{Number(alert.risk_score).toFixed(1)} / 100</span></td>
                    <td className="max-w-xs px-3 py-3">{alert.reasons?.length ? alert.reasons.join('; ') : 'No reason details provided'}</td>
                    <td className="px-3 py-3"><span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-semibold text-slate-700">{displayStatus(alert.status)}</span></td>
                    <td className="px-3 py-3"><StatusActions item={alert} kind="alert" onUpdate={handleStatusUpdate} onCreateCase={handleCreateCase} busy={busy} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-card-soft sm:p-5" aria-labelledby="active-cases-title">
        <div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-3">
          <FileSearch className="h-4 w-4 text-blue-700" aria-hidden="true" />
          <div>
            <h3 id="active-cases-title" className="text-sm font-bold text-slate-800">Investigation cases</h3>
            <p className="text-xs text-slate-500">Analyst case outcomes are stored separately from transaction risk decisions.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-xs text-slate-600">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Case</th>
                <th className="px-3 py-2.5">Customer</th>
                <th className="px-3 py-2.5">Risk score</th>
                <th className="px-3 py-2.5">Assigned analyst</th>
                <th className="px-3 py-2.5">Status</th>
                <th className="px-3 py-2.5 text-right">Analyst actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr><td colSpan={6} className="py-10 text-center text-slate-500">Loading active cases...</td></tr>
              ) : visibleCases.length === 0 ? (
                <tr><td colSpan={6} className="py-10 text-center text-slate-500">No active cases match this filter.</td></tr>
              ) : visibleCases.map((item) => {
                const style = getRiskStyle('', item.risk_score);
                const busy = savingId === `case:${item.case_id}`;
                return (
                  <tr key={item.id}>
                    <td className="px-3 py-3"><span className="block font-mono font-semibold text-teal-800">{item.case_id}</span><span className="mt-1 block text-slate-700">{item.title}</span></td>
                    <td className="px-3 py-3 font-mono">{item.customer_id}</td>
                    <td className="px-3 py-3"><span className={style.text}>{Number(item.risk_score).toFixed(1)} / 100</span></td>
                    <td className="px-3 py-3">{item.assigned_analyst || 'Unassigned'}</td>
                    <td className="px-3 py-3"><span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-semibold text-slate-700">{displayStatus(item.status)}</span></td>
                    <td className="px-3 py-3"><StatusActions item={item} kind="case" onUpdate={handleStatusUpdate} onCreateCase={handleCreateCase} busy={busy} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
