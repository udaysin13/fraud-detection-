import React, { useState } from 'react';
import {
  Shield,
  Search,
  Plus,
  Download,
  Bell,
  Settings,
  Globe,
  Clock,
  DollarSign,
  AlertTriangle,
  X,
  Radio,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const Header = () => {
  const {
    region,
    setRegion,
    timeRange,
    setTimeRange,
    currency,
    setCurrency,
    searchQuery,
    setSearchQuery,
    setIsCreateAlertOpen,
    notifications,
    unreadCount,
    clearNotifications,
    wsConnected,
  } = useFilter();

  const [isNotifOpen, setIsNotifOpen] = useState(false);

  const handleExportCSV = () => {
    window.open('http://localhost:8000/api/export?type=csv', '_blank');
  };

  const handleToggleNotif = () => {
    setIsNotifOpen(!isNotifOpen);
    if (!isNotifOpen) {
      clearNotifications();
    }
  };

  return (
    <header className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft px-5 py-3.5 mb-6 flex flex-wrap items-center justify-between gap-4 relative z-40">
      {/* Brand Logo & Live Engine Status */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#1B212C] to-slate-800 flex items-center justify-center shadow-md">
          <Shield className="w-6 h-6 text-[#F97316]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-tight flex items-center gap-0.5">
              <span className="text-[#1B212C]">Vault</span>
              <span className="text-[#F97316]">Guard</span>
            </h1>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                wsConnected
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  : 'bg-amber-50 text-amber-600 border border-amber-200'
              }`}
            >
              <Radio className={`w-3 h-3 ${wsConnected ? 'animate-pulse' : ''}`} />
              <span>{wsConnected ? 'Live Feed' : 'Connecting'}</span>
            </span>
          </div>
          <p className="text-[11px] font-medium text-gray-500 tracking-wide">
            Micro-Transaction Security Engine
          </p>
        </div>
      </div>

      {/* Center Filter Dropdowns */}
      <div className="flex items-center flex-wrap gap-2.5">
        {/* Region */}
        <div className="relative flex items-center">
          <Globe className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="pl-9 pr-8 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500/20 appearance-none cursor-pointer"
          >
            <option value="EU Payments">EU Payments</option>
            <option value="APAC Cards">APAC Cards</option>
            <option value="AU Cards">AU Cards</option>
            <option value="ME Cards">ME Cards</option>
            <option value="AS Cards">AS Cards</option>
          </select>
          <div className="pointer-events-none absolute right-2.5 text-gray-400 text-[10px]">▼</div>
        </div>

        {/* Time Range */}
        <div className="relative flex items-center">
          <Clock className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="pl-9 pr-8 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500/20 appearance-none cursor-pointer"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">7 days</option>
            <option value="30d">30 days</option>
          </select>
          <div className="pointer-events-none absolute right-2.5 text-gray-400 text-[10px]">▼</div>
        </div>

        {/* Currency */}
        <div className="relative flex items-center">
          <DollarSign className="w-4 h-4 text-gray-400 absolute left-3 pointer-events-none" />
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="pl-9 pr-8 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500/20 appearance-none cursor-pointer"
          >
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
            <option value="INR">INR (₹)</option>
          </select>
          <div className="pointer-events-none absolute right-2.5 text-gray-400 text-[10px]">▼</div>
        </div>
      </div>

      {/* Right Search, Create Alert & Action Icons */}
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative min-w-[220px]">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search transactions, customers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-orange-500/30 transition-all"
          />
        </div>

        {/* Create Alert Button */}
        <button
          onClick={() => setIsCreateAlertOpen(true)}
          className="flex items-center gap-1.5 bg-[#F97316] hover:bg-[#EA580C] text-white px-3.5 py-2 rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all transform active:scale-95"
        >
          <Plus className="w-4 h-4 stroke-[3]" />
          <span>Create Alert</span>
        </button>

        {/* Quick Icons */}
        <div className="flex items-center gap-1.5 border-l border-gray-200 pl-3 relative">
          <button
            onClick={handleExportCSV}
            title="Download CSV Report"
            className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={handleToggleNotif}
              title="Real-Time Alerts"
              className="relative p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-[#F97316] text-white text-[9px] font-black rounded-full flex items-center justify-center ring-2 ring-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Slide Down Notification Dropdown */}
            {isNotifOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-2xl border border-gray-200 p-4 z-50 animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-[#F97316]" />
                    <h4 className="text-xs font-extrabold text-slate-900">
                      Live High-Risk Alerts
                    </h4>
                  </div>
                  <button
                    onClick={() => setIsNotifOpen(false)}
                    className="p-1 text-gray-400 hover:text-slate-800 rounded-lg hover:bg-gray-100"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                  {notifications.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">
                      No new high-risk transactions detected yet.
                    </p>
                  ) : (
                    notifications.map((n) => (
                      <div
                        key={n.id}
                        className="bg-orange-50/60 border border-orange-200/80 rounded-xl p-3 text-xs space-y-1 hover:bg-orange-50 transition-colors"
                      >
                        <div className="flex justify-between items-center font-bold">
                          <span className="font-mono text-slate-900">{n.txnId}</span>
                          <span className="text-rose-600 bg-rose-100 px-2 py-0.5 rounded text-[10px]">
                            Risk: {n.riskScore}
                          </span>
                        </div>
                        <p className="text-slate-700 font-medium">
                          Amount: <strong>${n.amount}</strong>
                        </p>
                        <p className="text-[11px] text-slate-500 truncate">
                          {n.reasons ? n.reasons[0] : 'High risk anomaly'}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <button
            title="Settings"
            className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
