import React, { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  Search,
  Filter,
  AlertTriangle,
  UserCheck,
  Plus,
  RefreshCw,
  CheckCircle2,
  Clock,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';
import { BackendErrorBanner } from '../components/BackendErrorBanner';

export const Alerts = () => {
  const { searchQuery, setSearchQuery, setIsCreateAlertOpen } = useFilter();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [statusFilter, setStatusFilter] = useState('All');
  const [segmentFilter, setSegmentFilter] = useState('All');
  const [severityFilter, setSeverityFilter] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getAlerts({
        limit: 50,
        status: statusFilter,
        segment: segmentFilter,
        severity: severityFilter,
        search: searchQuery,
      });
      setAlerts(data || []);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
      setError(err.message || 'Unable to retrieve alert records.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, segmentFilter, severityFilter, searchQuery]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleUpdateAlert = async (alertId, payload) => {
    try {
      const updated = await apiClient.updateAlert(alertId, payload);
      // PATCH responses may contain only an acknowledgement. Preserve the
      // existing alert details while applying any returned fields/status.
      const mergeAlert = (alert) => ({
        ...alert,
        ...(updated || {}),
        status:
          updated?.status ||
          updated?.new_status ||
          payload?.status ||
          alert.status,
      });
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? mergeAlert(alert) : alert
        )
      );
      setSelectedAlert((current) =>
        current?.id === alertId ? mergeAlert(current) : current
      );
    } catch (err) {
      console.error('Failed to update alert status:', err);
    }
  };

  const handleUpdateAlertStatus = (alertId, newStatus) =>
    handleUpdateAlert(alertId, { status: newStatus });

  const getStatusBadgeStyle = (status) => {
    switch (status) {
      case 'Monitoring':
        return 'bg-amber-50 text-amber-600 border-amber-200';
      case 'Investigating':
        return 'bg-teal-50 text-teal-600 border-teal-200';
      case 'Resolved':
        return 'bg-emerald-50 text-emerald-600 border-emerald-200';
      case 'Dismissed':
        return 'bg-slate-100 text-slate-400 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="space-y-5">
      {/* Header Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-50 border border-amber-200 text-amber-600 rounded-xl">
            <Bell className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Security Alerts & Incident Triage</h2>
            <p className="text-xs text-slate-400">
              Operational alert queues, analyst assignment rosters, and review workflow
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsCreateAlertOpen(true)}
            className="px-3.5 py-2 bg-teal-600 hover:bg-teal-500 text-slate-800 rounded-lg text-xs font-bold shadow-md transition-all flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>Create Alert</span>
          </button>
        </div>
      </div>

      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={fetchAlerts}
          isRetrying={loading}
        />
      )}

      {/* Main Table Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
        {/* Controls Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search alerts, titles, codes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="All">All Statuses</option>
              <option value="Monitoring">Monitoring</option>
              <option value="Investigating">Investigating</option>
              <option value="Resolved">Resolved</option>
              <option value="Dismissed">Dismissed</option>
            </select>

            {/* Segment Filter */}
            <select
              value={segmentFilter}
              onChange={(e) => setSegmentFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
            >
              <option value="All">All Segments</option>
              <option value="UPI P2P">UPI P2P</option>
              <option value="UPI P2M QR">UPI P2M QR</option>
              <option value="Digital Wallet">Digital Wallet</option>
              <option value="IMPS">IMPS</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 font-semibold focus:outline-none focus:border-teal-500"
              aria-label="Filter by alert severity"
            >
              <option value="All">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            <button
              onClick={fetchAlerts}
              className="p-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-400 hover:text-slate-800 transition-colors"
              title="Refresh Alerts"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Alerts Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-400 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Alert Code</th>
                <th className="py-2.5 px-3">Anomaly Title</th>
                <th className="py-2.5 px-3">Payment Segment</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Assigned Analyst</th>
                <th className="py-2.5 px-3">Time</th>
                <th className="py-2.5 px-3">Review Status</th>
                <th className="py-2.5 px-3 text-right">Quick Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-teal-600 mx-auto mb-2" />
                    <p>Loading security alert logs...</p>
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 italic">
                    No alerts found for current criteria.
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <tr
                    key={a.id}
                    onClick={() => setSelectedAlert(a)}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    <td className="py-3 px-3 font-mono text-teal-600 font-bold">
                      {a.alert_code}
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-800 max-w-sm truncate">
                      {a.title}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-400">
                      {a.segment}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`rounded border px-2 py-0.5 text-[10px] font-bold ${a.severity === 'CRITICAL' ? 'border-rose-200 bg-rose-50 text-rose-700' : a.severity === 'HIGH' ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-slate-200 bg-slate-50 text-slate-600'}`}>
                        {a.severity || 'MEDIUM'}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-600">
                      {a.assignee}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-400 whitespace-nowrap">
                      {a.time_ago}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadgeStyle(a.status)}`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        {a.status !== 'Resolved' ? (
                          <button
                            onClick={() => handleUpdateAlertStatus(a.id, 'Resolved')}
                            className="px-2 py-1 rounded bg-emerald-50 hover:bg-emerald-50 text-emerald-600 border border-emerald-200 text-[10px] font-bold transition-colors"
                          >
                            Resolve
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpdateAlertStatus(a.id, 'Monitoring')}
                            className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-700 text-slate-400 text-[10px] font-bold transition-colors"
                          >
                            Reopen
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedAlert(a)}
                          className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-700 text-teal-600 text-[10px] font-bold transition-colors"
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alert Drawer */}
      <AlertDetailDrawer
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onUpdateStatus={handleUpdateAlertStatus}
        onAcknowledge={(alertId, acknowledge) => handleUpdateAlert(alertId, { acknowledge })}
      />
    </div>
  );
};
