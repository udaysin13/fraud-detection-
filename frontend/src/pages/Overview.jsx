import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  ShieldAlert,
  AlertTriangle,
  TrendingUp,
  Activity,
  CreditCard,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RefreshCw,
  Cpu,
  Database,
  Radio,
  Clock,
  Layers,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { KpiCard } from '../components/KpiCard';
import { BackendErrorBanner } from '../components/BackendErrorBanner';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';
import {
  formatINR,
  formatIndianNumber,
  formatTimestamp,
  getRiskStyle,
  getChannelLabel,
} from '../utils/formatters';

const buildTrendFallback = (transactions = []) => {
  // The bundled/demo dataset can be older than the selected 24h/7d/30d window.
  // Group the latest available persisted rows so the chart remains useful instead of blank.
  const groups = new Map();
  for (const txn of transactions) {
    const parsed = new Date(txn.timestamp);
    if (Number.isNaN(parsed.getTime())) continue;
    const bucket = parsed.toISOString().slice(0, 13).replace('T', ' ');
    const item = groups.get(bucket) || { timestamp: bucket, suspicious: 0, blocked: 0, manual_review: 0 };
    const decision = String(txn.decision || '').trim().toLowerCase();
    if (Number(txn.risk_score || 0) > 40) item.suspicious += 1;
    if (decision === 'block' || decision === 'blocked') item.blocked += 1;
    if (decision === 'manual review' || decision === 'manual_review' || decision === 'review') item.manual_review += 1;
    groups.set(bucket, item);
  }
  return [...groups.values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-24);
};

export const Overview = () => {
  const {
    timeRange,
    selectedChannel,
    setSelectedTransactionId,
    backendHealth,
    healthLoading,
    checkHealth,
    liveTransactions,
    wsStatus,
  } = useFilter();

  const [overview, setOverview] = useState(null);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [trendUsingFallback, setTrendUsingFallback] = useState(false);
  const [riskSummary, setRiskSummary] = useState(null);
  const [recentSuspicious, setRecentSuspicious] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retrying, setRetrying] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Load dashboard panels independently: a single failing endpoint must not blank every chart.
      const [overviewRes, trendRes, riskRes, suspiciousRes, alertsRes, metricsRes, fallbackTransactions] = await Promise.all([
        apiClient.getAnalyticsOverview().catch((err) => { console.error('Overview metrics failed:', err); return null; }),
        apiClient.getTrend(timeRange).catch((err) => { console.error('Trend endpoint failed:', err); return []; }),
        apiClient.getRiskScoreSummary().catch((err) => { console.error('Risk summary failed:', err); return null; }),
        apiClient.getTransactions({ limit: 6, risk_category: 'HIGH_RISK' }).catch((err) => { console.error('Suspicious transactions failed:', err); return []; }),
        apiClient.getAlerts({ limit: 5 }).catch((err) => { console.error('Alerts failed:', err); return []; }),
        apiClient.getModelMetrics().catch((err) => { console.error('Model metrics failed:', err); return null; }),
        apiClient.getTransactions({ limit: 100 }).catch((err) => { console.error('Trend fallback records failed:', err); return []; }),
      ]);

      setOverview(overviewRes);
      // A non-empty API response can still contain only zeroes. Treat it as
      // unusable chart data and derive the series from the latest transaction rows.
      const hasMeaningfulTrend = Array.isArray(trendRes) && trendRes.some((point) =>
        Number(point?.blocked || 0) > 0 ||
        Number(point?.manual_review || 0) > 0 ||
        Number(point?.suspicious || 0) > 0
      );
      const fallbackRows = Array.isArray(fallbackTransactions)
        ? fallbackTransactions
        : Array.isArray(fallbackTransactions?.items)
          ? fallbackTransactions.items
          : [];
      const fallbackTrend = hasMeaningfulTrend ? [] : buildTrendFallback(fallbackRows);
      setTrendData(hasMeaningfulTrend ? trendRes : fallbackTrend);
      setTrendUsingFallback(!hasMeaningfulTrend && fallbackTrend.length > 0);
      setRiskSummary(riskRes);
      setRecentSuspicious(suspiciousRes || []);
      setRecentAlerts(alertsRes || []);
      setModelMetrics(metricsRes);
      if (!overviewRes && (!fallbackTransactions || fallbackTransactions.length === 0)) {
        setError('Dashboard data could not be loaded. Please check backend health and retry.');
      } else {
        setError(null);
      }
    } catch (err) {
      console.error('Failed to fetch overview data:', err);
      setError(err.message || 'Unable to connect to VaultGuard backend service.');
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRetry = () => {
    setRetrying(true);
    checkHealth();
    fetchDashboardData();
  };

  const handleUpdateAlertStatus = async (alertId, newStatus) => {
    try {
      const updated = await apiClient.updateAlert(alertId, { status: newStatus });
      setRecentAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? updated : a))
      );
      if (selectedAlert && selectedAlert.id === alertId) {
        setSelectedAlert(updated);
      }
    } catch (err) {
      console.error('Failed to update alert:', err);
    }
  };

  // Risk Distribution Data for Donut Chart
  const riskDistributionData = overview
    ? [
        { name: 'Low Risk (Allow)', value: overview.total_allowed, color: '#10B981' },
        { name: 'Manual Review', value: overview.total_review, color: '#F59E0B' },
        { name: 'Blocked (High Risk)', value: overview.total_blocked, color: '#EF4444' },
      ]
    : [];

  // Top Risk Factors / Contributors
  const topContributors = riskSummary?.top_contributors || [];

  return (
    <div className="space-y-6">
      {/* Backend Error Banner if API connection fails */}
      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={handleRetry}
          isRetrying={retrying}
        />
      )}

      {/* Model & System Health Readiness Strip */}
      <div className="bg-[#111827] border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-card-dark text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center shrink-0">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-sm">
                VaultGuard model: {backendHealth?.model_version || 'Version unavailable'}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                Academic prototype
              </span>
            </div>
            <p className="text-slate-400 text-[11px] mt-0.5">
              Synthetic Indian digital-payment data; estimates may be incorrect.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-300">
            <Database className="w-3.5 h-3.5 text-teal-400" />
                <span>Database records: </span>
            <strong className="text-white">
              {formatIndianNumber(overview?.total_transactions || backendHealth?.transaction_count || 0)}
            </strong>
          </div>

          <div className="flex items-center gap-1.5 text-slate-300">
            <Radio className={`w-3.5 h-3.5 ${wsStatus === 'connected' ? 'text-teal-400 animate-pulse' : 'text-slate-500'}`} />
                <span>Simulated feed: </span>
            <strong className={wsStatus === 'connected' ? 'text-teal-400' : 'text-slate-400'}>
              {wsStatus === 'connected' ? 'Connected' : wsStatus === 'reconnecting' ? 'Reconnecting' : 'Disconnected'}
            </strong>
          </div>

          <button
            onClick={handleRetry}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
            title="Refresh Dashboard Metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Transactions Analyzed"
          value={formatIndianNumber(overview?.total_transactions || 0)}
          subtitle="Records in the database"
          icon={Activity}
          tooltip="Count of persisted transaction records currently in the database."
          accentColor="teal"
          loading={loading}
        />

        <KpiCard
          title="Dataset Fraud Labels"
          value={formatIndianNumber(overview?.dataset_fraud_labels || 0)}
          subtitle="Ground-truth labels in stored data"
          icon={ShieldAlert}
          tooltip="Count of records labeled as fraud in the dataset; this is separate from model risk flags."
          accentColor="rose"
          loading={loading}
        />

        <KpiCard
          title="High-Risk Transactions"
          value={formatIndianNumber(overview?.total_blocked || 0)}
          subtitle={`${formatIndianNumber(overview?.total_fraud_flagged || 0)} records have risk score above 40`}
          icon={AlertTriangle}
          tooltip="High-risk decision count from the database. The companion count includes records with a risk score above 40."
          accentColor="amber"
          loading={loading}
        />

        <KpiCard
          title="Model Performance"
          value={modelMetrics ? `${(modelMetrics.f1_score * 100).toFixed(1)}% F1` : '—'}
          subtitle="Synthetic holdout; not real-world accuracy"
          icon={Cpu}
          tooltip="F1 score reported by the saved model evaluation metrics for the synthetic chronological test split."
          accentColor="blue"
          loading={loading}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Transaction risk overview</h2>
          <p className="text-xs text-slate-500">Database analytics and explicitly simulated stream events are shown separately.</p>
        </div>
        <Link to="/fraud-detection" className="inline-flex items-center gap-2 rounded-md bg-[#0F766E] px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-700 focus-visible:outline-offset-2">
          <ShieldAlert className="h-4 w-4" aria-hidden="true" />
          Analyze a Transaction
        </Link>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Main Trend Time-Series Chart (8 Cols) */}
        <div className="lg:col-span-8 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Risk decisions over time</span>
                <span className="text-[10px] font-normal px-2 py-0.5 rounded bg-slate-800 text-teal-400">
                  Range: {timeRange}
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {trendUsingFallback ? 'Latest available database records (no recent records in selected window)' : 'Persisted transaction counts by time bucket and decision category'}
              </p>
            </div>
          </div>

          <div className="h-64 sm:h-72 w-full">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <RefreshCw className="w-6 h-6 animate-spin text-teal-400" />
              </div>
            ) : trendData.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
                <Clock className="w-8 h-8 mb-2 opacity-50" />
                <p>No transaction timestamps are available to plot.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="timestamp"
                    stroke="#64748B"
                    tick={{ fill: '#94A3B8', fontSize: 10 }}
                    tickFormatter={(val) => String(val || '').split(' ').pop() || String(val || '')}
                  />
                  <YAxis stroke="#64748B" tick={{ fill: '#94A3B8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#111827',
                      borderColor: '#1F293D',
                      borderRadius: '8px',
                      color: '#F8FAFC',
                      fontSize: '11px',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                    iconType="circle"
                  />
                  <Line
                    type="monotone"
                    dataKey="blocked"
                    name="Blocked (High Risk)"
                    stroke="#EF4444"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="manual_review"
                    name="Manual Review"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="suspicious"
                    name="Total Flagged (>40)"
                    stroke="#0D9488"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Risk Distribution Donut Chart (4 Cols) */}
        <div className="lg:col-span-4 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark flex flex-col justify-between">
          <div className="pb-3 border-b border-slate-800/80 mb-3">
            <h3 className="text-sm font-bold text-white">Risk Category Breakdown</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Decisions distribution on scored population
            </p>
          </div>

          <div className="h-52 w-full relative flex items-center justify-center">
            {loading ? (
              <RefreshCw className="w-6 h-6 animate-spin text-teal-400" />
            ) : riskDistributionData.every((item) => Number(item.value || 0) === 0) ? (
              <div className="px-4 text-center text-xs text-slate-400">
                <Layers className="mx-auto mb-2 h-7 w-7 opacity-60" />
                <p>No decision counts are available yet.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {riskDistributionData.map((entry, idx) => (
                      <Cell key={`cell-${idx}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val) => [formatIndianNumber(val), 'Count']}
                    contentStyle={{
                      backgroundColor: '#111827',
                      borderColor: '#1F293D',
                      borderRadius: '8px',
                      color: '#F8FAFC',
                      fontSize: '11px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Legend Items */}
          <div className="space-y-1.5 pt-2 border-t border-slate-800 text-xs">
            {riskDistributionData.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-300">{item.name}</span>
                </div>
                <span className="font-mono font-bold text-white">
                  {formatIndianNumber(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Secondary Row: Top Risk Contributors & Live Ticker Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Top Anomaly Contributors (5 Cols) */}
        <div className="lg:col-span-5 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark">
          <div className="pb-3 border-b border-slate-800/80 mb-4">
            <h3 className="text-sm font-bold text-white">Common stored reason text</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Most common reason strings among flagged database records; not a SHAP importance summary
            </p>
          </div>

          <div className="space-y-3">
            {topContributors.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No contributor data available.</p>
            ) : (
              topContributors.map((c, i) => (
                <div key={i} className="space-y-1 text-xs">
                  <div className="flex justify-between text-slate-300">
                    <span className="truncate pr-2 font-medium">{c.name}</span>
                    <span className="font-mono text-teal-400 font-bold shrink-0">{c.percentage}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-teal-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(c.percentage * 2, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Live WebSocket Simulated Feed (7 Cols) */}
        <div className="lg:col-span-7 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
            <div className="flex items-center gap-2">
              <Radio className={`w-4 h-4 ${wsStatus === 'connected' ? 'text-teal-400 animate-pulse' : 'text-slate-500'}`} />
              <div>
                <h3 className="text-sm font-bold text-white">Live Stream Ticker (Simulated)</h3>
                <span className="text-[10px] text-slate-500 block">
                  Simulated events for real-time latency evaluation • Distinct from database history
                </span>
              </div>
            </div>

            <Link
              to="/transactions"
              className="text-xs text-teal-400 hover:text-teal-300 flex items-center gap-1 font-bold"
            >
              <span>Explore All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {liveTransactions.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 space-y-1">
                <Clock className="w-6 h-6 mx-auto opacity-50 mb-1" />
                <p>Awaiting live transactions from WebSocket endpoint...</p>
                <p className="text-[11px] text-slate-600">Simulated transactions stream every ~3s</p>
              </div>
            ) : (
              liveTransactions.slice(0, 5).map((t, idx) => {
                const style = getRiskStyle(t.decision, t.risk_score);
                return (
                  <div
                    key={t.transaction_id + idx}
                    onClick={() => setSelectedTransactionId(t.transaction_id)}
                    className="bg-[#161F30] border border-slate-800 rounded-lg p-2.5 flex items-center justify-between gap-3 text-xs hover:border-slate-700 transition-colors cursor-pointer"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-teal-400 font-bold truncate">
                          {t.transaction_id}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {getChannelLabel(t.channel)}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">
                        {t.reasons ? t.reasons[0] : 'Normal parameters'}
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="font-bold text-white">
                        {formatINR(t.amount_inr ?? t.amount)}
                      </div>
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border mt-0.5 ${style.bg} ${style.border} ${style.text}`}>
                        {t.decision} ({t.risk_score})
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Recent High-Risk Transactions & Security Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Recent High-Risk Transactions Table (7 Cols) */}
        <div className="lg:col-span-7 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                Recent High-Risk Transactions
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Database records flagged by XGBoost + Isolation Forest
              </p>
            </div>
            <Link
              to="/transactions?decision=Block"
              className="text-xs text-teal-400 hover:text-teal-300 font-bold flex items-center gap-1"
            >
              <span>View All Blocked</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-[#161F30] text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-2 px-3">Transaction ID</th>
                  <th className="py-2 px-3">Channel</th>
                  <th className="py-2 px-3">Amount</th>
                  <th className="py-2 px-3">Risk Score</th>
                  <th className="py-2 px-3">Decision</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {recentSuspicious.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500 italic">
                      No high-risk transactions recorded.
                    </td>
                  </tr>
                ) : (
                  recentSuspicious.map((r) => {
                    const style = getRiskStyle(r.decision, r.risk_score);
                    return (
                      <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-mono text-teal-400 font-bold">
                          {r.transaction_id}
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-slate-400">
                          {r.channel}
                        </td>
                        <td className="py-2.5 px-3 font-bold text-white">
                          {formatINR(r.amount_inr ?? r.amount)}
                        </td>
                        <td className="py-2.5 px-3 font-bold">
                          <span className={style.text}>{r.risk_score}</span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${style.bg} ${style.border} ${style.text}`}>
                            {r.decision}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => setSelectedTransactionId(r.transaction_id)}
                            className="text-teal-400 hover:text-teal-300 text-[11px] font-bold"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Incident Alerts (5 Cols) */}
        <div className="lg:col-span-5 bg-[#111827] border border-slate-800 rounded-xl p-5 shadow-card-dark">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Security Alerts Roster
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Investigator triage and rule monitor feeds
              </p>
            </div>
            <Link
              to="/alerts"
              className="text-xs text-teal-400 hover:text-teal-300 font-bold flex items-center gap-1"
            >
              <span>Manage</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {recentAlerts.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center italic">
                No active security alerts in feed.
              </p>
            ) : (
              recentAlerts.map((a) => (
                <div
                  key={a.id}
                  onClick={() => setSelectedAlert(a)}
                  className="bg-[#161F30] border border-slate-800 rounded-lg p-3 text-xs space-y-1 hover:border-slate-700 transition-colors cursor-pointer"
                >
                  <div className="flex justify-between items-center font-bold">
                    <span className="font-mono text-teal-400 text-[11px]">{a.alert_code}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      a.status === 'Investigating'
                        ? 'bg-teal-500/15 text-teal-400'
                        : a.status === 'Resolved'
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'bg-amber-500/15 text-amber-400'
                    }`}>
                      {a.status}
                    </span>
                  </div>
                  <p className="text-slate-200 font-medium truncate">{a.title}</p>
                  <div className="flex justify-between text-slate-400 text-[11px] pt-1">
                    <span>{a.segment}</span>
                    <span>{a.assignee}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Alert Detail Drawer if selected */}
      <AlertDetailDrawer
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onUpdateStatus={handleUpdateAlertStatus}
      />
    </div>
  );
};
