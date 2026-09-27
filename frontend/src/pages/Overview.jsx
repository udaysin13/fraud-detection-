import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Filter,
  ArrowUpRight,
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';

export const Overview = () => {
  const { region, timeRange, currency, searchQuery } = useFilter();

  const [riskData, setRiskData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // Fetch telemetry data from backend endpoints
  const fetchData = async () => {
    setLoading(true);
    try {
      const [riskRes, trendRes, alertsRes] = await Promise.all([
        fetch('http://localhost:8000/api/risk-score'),
        fetch(`http://localhost:8000/api/trend?range=${timeRange}`),
        fetch(`http://localhost:8000/api/alerts?limit=6`),
      ]);

      const riskJson = await riskRes.json();
      const trendJson = await trendRes.json();
      const alertsJson = await alertsRes.json();

      setRiskData(riskJson);
      setTrendData(trendJson);
      setAlerts(alertsJson);
    } catch (error) {
      console.error('Error fetching overview metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [region, timeRange, currency]);

  // Handle alert status update
  const handleUpdateAlertStatus = async (alertId, newStatus) => {
    try {
      const res = await fetch(`http://localhost:8000/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAlerts((prev) =>
          prev.map((a) => (a.id === alertId ? updated : a))
        );
        if (selectedAlert && selectedAlert.id === alertId) {
          setSelectedAlert(updated);
        }
      }
    } catch (err) {
      console.error('Failed to update alert:', err);
    }
  };

  // Filter alerts by search query
  const filteredAlerts = alerts.filter(
    (a) =>
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.alert_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.segment.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Donut chart data
  const flaggedCount = riskData?.flagged_count || 1549;
  const pieData = [
    { name: 'Flagged Risk', value: flaggedCount, color: '#F97316' },
    { name: 'Normal', value: 55000 - flaggedCount, color: '#E5E7EB' },
  ];

  const topContributorsList = [
    { name: 'Unusual velocity', pct: 28.5 },
    { name: 'New device surge', pct: 24.2 },
    { name: 'Geo mismatch', pct: 21.0 },
    { name: 'High-risk BIN range', pct: 14.8 },
    { name: 'Merchant anomaly', pct: 11.5 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Title & Subtitle Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Risk Overview
          </h2>
          <p className="text-xs font-medium text-slate-500 mt-0.5">
            Real-time monitoring of transaction risk and fraud indications
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border transition-all ${
              showFilterPanel
                ? 'bg-[#1B212C] text-white border-[#1B212C]'
                : 'bg-gray-50 text-slate-700 border-gray-200 hover:bg-gray-100'
            }`}
          >
            <Filter className="w-3.5 h-3.5 text-[#F97316]" />
            <span>Filters</span>
          </button>

          <button
            onClick={fetchData}
            className="p-2 bg-gray-50 hover:bg-gray-100 text-slate-600 border border-gray-200 rounded-xl transition-colors"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Optional Active Filters Indicator Bar */}
      {showFilterPanel && (
        <div className="bg-slate-900 text-white p-4 rounded-[16px] flex flex-wrap items-center justify-between gap-3 text-xs animate-in slide-in-from-top-2">
          <div className="flex items-center gap-4">
            <span className="font-bold text-slate-400">Active Scope:</span>
            <span className="bg-slate-800 px-3 py-1 rounded-lg border border-slate-700 font-semibold">
              Region: <strong className="text-[#F97316]">{region}</strong>
            </span>
            <span className="bg-slate-800 px-3 py-1 rounded-lg border border-slate-700 font-semibold">
              Window: <strong className="text-[#14B8A6]">{timeRange}</strong>
            </span>
            <span className="bg-slate-800 px-3 py-1 rounded-lg border border-slate-700 font-semibold">
              Currency: <strong className="text-white">{currency}</strong>
            </span>
          </div>
          <button
            onClick={() => setShowFilterPanel(false)}
            className="text-xs text-slate-400 hover:text-white underline"
          >
            Hide Filters
          </button>
        </div>
      )}

      {/* Grid Row 1: Health Score Card & Trend Timeline Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Card 1: Risk Health Score Card (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900">
                Risk Health Score
              </h3>
              <a
                href="#contributors"
                className="text-xs font-bold text-[#F97316] hover:underline flex items-center gap-0.5"
              >
                <span>View details</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Donut Chart with Centered Count */}
            <div className="relative h-48 w-full flex items-center justify-center my-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={62}
                    outerRadius={82}
                    startAngle={90}
                    endAngle={-270}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Centered Donut Label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {loading ? '...' : flaggedCount.toLocaleString()}
                </span>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Flagged Txns
                </span>
              </div>
            </div>

            {/* Change Percentage Pill */}
            <div className="flex justify-center mb-5">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-extrabold bg-orange-50 text-[#F97316] border border-orange-200 shadow-sm">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>+5.2% vs prev window ▲</span>
              </span>
            </div>
          </div>

          {/* Top Contributors List */}
          <div id="contributors" className="space-y-3 pt-3 border-t border-gray-100">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Top Risk Contributors
            </h4>
            <div className="space-y-2.5">
              {topContributorsList.map((item) => (
                <div key={item.name} className="space-y-1">
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-slate-700">{item.name}</span>
                    <span className="text-slate-900 font-bold">{item.pct}%</span>
                  </div>
                  <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-[#F97316] h-full rounded-full transition-all duration-500"
                      style={{ width: `${item.pct * 3}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Card 2: Risk Trend Timeline Card (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Risk Trend Timeline
                </h3>
                <p className="text-xs text-slate-400 font-medium">
                  Hourly velocity & threat breakdown ({timeRange})
                </p>
              </div>
              <button
                onClick={() => alert('Comparing current period against baseline 30-day average.')}
                className="text-xs font-bold text-[#F97316] hover:underline flex items-center gap-0.5"
              >
                <span>Compare periods</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Recharts Line Chart */}
            <div className="h-64 w-full mt-2">
              {loading ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-400">
                  Loading timeline graph...
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                    <XAxis
                      dataKey="timestamp"
                      tick={{ fontSize: 10, fill: '#64748B' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: '#64748B' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1B212C',
                        borderColor: '#334155',
                        borderRadius: '12px',
                        color: '#fff',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="suspicious"
                      name="Suspicious Flagged"
                      stroke="#F97316"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: '#F97316' }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="blocked"
                      name="Blocked"
                      stroke="#1B212C"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: '#1B212C' }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="manual_review"
                      name="Manual Reviews"
                      stroke="#14B8A6"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: '#14B8A6' }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Styled Legend in Rounded Grey Bar */}
          <div className="mt-4 pt-3 border-t border-gray-100 flex justify-center">
            <div className="bg-slate-100 rounded-full px-5 py-2 flex flex-wrap items-center justify-center gap-6 text-xs font-bold text-slate-700 shadow-inner">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F97316]"></span>
                <span>Suspicious Flagged</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#1B212C]"></span>
                <span>Blocked</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#14B8A6]"></span>
                <span>Manual Reviews</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grid Row 2: Top Alerts & Incidents Table Card */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Top Alerts & Incidents
            </h3>
            <p className="text-xs text-slate-400 font-medium">
              High priority micro-fraud vectors and security rule triggers
            </p>
          </div>
          <Link
            to="/alerts"
            className="text-xs font-bold text-[#F97316] hover:underline flex items-center gap-0.5"
          >
            <span>View all alerts</span>
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Alerts Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-200/80">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#E5E9F2] text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-gray-200">
                <th className="py-3 px-4 w-12 text-center">Severity</th>
                <th className="py-3 px-4">Alert Title & Code</th>
                <th className="py-3 px-4">Segment</th>
                <th className="py-3 px-4">Started</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Assignee</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-700 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    Loading security alerts...
                  </td>
                </tr>
              ) : filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No active alerts found matching search criteria.
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((alert) => (
                  <tr
                    key={alert.id}
                    onClick={() => setSelectedAlert(alert)}
                    className="hover:bg-slate-50 transition-colors cursor-pointer group"
                  >
                    {/* Severity Icon */}
                    <td className="py-3.5 px-4 text-center">
                      <div className="w-7 h-7 rounded-lg bg-orange-100 text-[#F97316] flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                        <AlertTriangle className="w-4 h-4" />
                      </div>
                    </td>

                    {/* Alert Code & Title */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-bold text-slate-900 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
                          {alert.alert_code}
                        </span>
                        <span className="font-semibold text-slate-900 group-hover:text-[#F97316] transition-colors">
                          {alert.title}
                        </span>
                      </div>
                    </td>

                    {/* Segment */}
                    <td className="py-3.5 px-4">
                      <span className="inline-block px-2.5 py-1 rounded-lg bg-gray-100 text-slate-700 font-semibold text-[11px]">
                        {alert.segment}
                      </span>
                    </td>

                    {/* Started */}
                    <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                      {alert.time_ago}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-[11px] font-bold border ${
                          alert.status === 'Monitoring'
                            ? 'bg-orange-50 text-[#F97316] border-orange-200'
                            : alert.status === 'Investigating'
                            ? 'bg-teal-50 text-[#14B8A6] border-teal-200'
                            : 'bg-[#1B212C] text-white border-[#1B212C]'
                        }`}
                      >
                        {alert.status}
                      </span>
                    </td>

                    {/* Owner */}
                    <td className="py-3.5 px-4 font-semibold text-slate-800">
                      {alert.assignee}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-Over Alert Detail Drawer */}
      <AlertDetailDrawer
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onUpdateStatus={handleUpdateAlertStatus}
      />
    </div>
  );
};
