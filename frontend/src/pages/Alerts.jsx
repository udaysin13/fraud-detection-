import React, { useState, useEffect } from 'react';
import { Bell, Search, Filter, AlertTriangle, UserCheck } from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { AlertDetailDrawer } from '../components/AlertDetailDrawer';

export const Alerts = () => {
  const { searchQuery, setSearchQuery, setIsCreateAlertOpen } = useFilter();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('All');
  const [segmentFilter, setSegmentFilter] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/api/alerts?limit=50';
      if (statusFilter !== 'All') url += `&status=${encodeURIComponent(statusFilter)}`;
      if (segmentFilter !== 'All') url += `&segment=${encodeURIComponent(segmentFilter)}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();
      setAlerts(data);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter, segmentFilter, searchQuery]);

  const handleUpdateAlertStatus = async (alertId, newStatus) => {
    try {
      const res = await fetch(`http://localhost:8000/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
        if (selectedAlert && selectedAlert.id === alertId) {
          setSelectedAlert(updated);
        }
      }
    } catch (err) {
      console.error('Failed to update alert status:', err);
    }
  };

  const handleUpdateAssignee = async (alertId, newAssignee) => {
    try {
      const res = await fetch(`http://localhost:8000/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignee: newAssignee }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
      }
    } catch (err) {
      console.error('Failed to update assignee:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-orange-100 text-[#F97316] rounded-xl">
            <Bell className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Security Alert Feed</h2>
            <p className="text-xs text-slate-500">Incident monitoring and analyst assignment roster</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsCreateAlertOpen(true)}
            className="px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl text-xs font-bold shadow-md transition-all"
          >
            + Create New Alert
          </button>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        {/* Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5 pb-4 border-b border-gray-100">
          <div className="relative min-w-[220px]">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search alert title, code, owner..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-slate-800 focus:ring-2 focus:ring-orange-500/30"
            />
          </div>

          <div className="flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700"
            >
              <option value="All">All Statuses</option>
              <option value="Monitoring">Monitoring</option>
              <option value="Investigating">Investigating</option>
              <option value="Pending Review">Pending Review</option>
              <option value="Resolved">Resolved</option>
            </select>

            <select
              value={segmentFilter}
              onChange={(e) => setSegmentFilter(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700"
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

        {/* Table */}
        <div className="overflow-x-auto rounded-xl border border-gray-200/80">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#E5E9F2] text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-gray-200">
                <th className="py-3 px-4 w-12 text-center">Sev</th>
                <th className="py-3 px-4">Alert Code & Description</th>
                <th className="py-3 px-4">Segment</th>
                <th className="py-3 px-4">Time Elapsed</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Assigned Analyst</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-700 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-400">
                    Loading alerts...
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-400">
                    No alerts match current parameters.
                  </td>
                </tr>
              ) : (
                alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4 text-center">
                      <div className="w-7 h-7 rounded-lg bg-orange-100 text-[#F97316] flex items-center justify-center mx-auto">
                        <AlertTriangle className="w-4 h-4" />
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-bold text-slate-900 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
                          {a.alert_code}
                        </span>
                        <span
                          onClick={() => setSelectedAlert(a)}
                          className="font-bold text-slate-900 hover:text-[#F97316] cursor-pointer transition-colors"
                        >
                          {a.title}
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-semibold">{a.segment}</td>
                    <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">{a.time_ago}</td>

                    <td className="py-3.5 px-4">
                      <select
                        value={a.status}
                        onChange={(e) => handleUpdateAlertStatus(a.id, e.target.value)}
                        className={`px-2.5 py-1 rounded-full text-[11px] font-bold border cursor-pointer ${
                          a.status === 'Monitoring'
                            ? 'bg-orange-50 text-[#F97316] border-orange-200'
                            : a.status === 'Investigating'
                            ? 'bg-teal-50 text-[#14B8A6] border-teal-200'
                            : 'bg-[#1B212C] text-white border-[#1B212C]'
                        }`}
                      >
                        <option value="Monitoring">Monitoring</option>
                        <option value="Investigating">Investigating</option>
                        <option value="Pending Review">Pending Review</option>
                        <option value="Resolved">Resolved</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-4">
                      <select
                        value={a.assignee}
                        onChange={(e) => handleUpdateAssignee(a.id, e.target.value)}
                        className="px-2.5 py-1 bg-gray-50 border border-gray-200 rounded-lg text-xs font-semibold text-slate-800"
                      >
                        <option value="Emily Wang">Emily Wang</option>
                        <option value="John Lee">John Lee</option>
                        <option value="Amina Hassan">Amina Hassan</option>
                        <option value="Mike Chen">Mike Chen</option>
                        <option value="Sara Lee">Sara Lee</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedAlert(a)}
                        className="text-xs font-bold text-[#F97316] hover:underline"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AlertDetailDrawer
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onUpdateStatus={handleUpdateAlertStatus}
      />
    </div>
  );
};
