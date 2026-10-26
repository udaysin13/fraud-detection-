import React, { useState } from 'react';
import {
  Shield,
  Search,
  Plus,
  Download,
  Bell,
  Info,
  Radio,
  Menu,
  X,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';
import { apiClient } from '../api/client';
import { formatINR } from '../utils/formatters';

export const Header = ({ onToggleMobileSidebar }) => {
  const {
    timeRange,
    setTimeRange,
    selectedChannel,
    setSelectedChannel,
    searchQuery,
    setSearchQuery,
    setIsCreateAlertOpen,
    setIsAboutModalOpen,
    setSelectedTransactionId,
    backendHealth,
    healthLoading,
    checkHealth,
    notifications,
    unreadCount,
    clearNotifications,
    wsStatus,
    manualReconnectWS,
  } = useFilter();

  const [isNotifOpen, setIsNotifOpen] = useState(false);

  const handleExportCSV = () => {
    window.open(apiClient.getExportUrl(), '_blank');
  };

  const handleToggleNotif = () => {
    setIsNotifOpen(!isNotifOpen);
    if (!isNotifOpen) {
      clearNotifications();
    }
  };

  return (
    <header className="bg-[#111827] border border-slate-800 rounded-xl px-4 py-3 shadow-card-dark mb-5 flex flex-wrap items-center justify-between gap-3 text-slate-200">
      {/* Left: Mobile Toggle & Brand Title */}
      <div className="flex items-center gap-3">
        {onToggleMobileSidebar && (
          <button
            onClick={onToggleMobileSidebar}
            className="lg:hidden p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center shrink-0">
          <Shield className="w-5 h-5" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-extrabold tracking-tight text-white flex items-center gap-1">
              <span>Vault</span>
              <span className="text-teal-400">Guard</span>
            </h1>

            {/* Model & API Status Badge */}
            <button
              onClick={() => checkHealth()}
              title="Click to refresh system health"
              className={`hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                backendHealth?.status === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20'
              }`}
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span>{backendHealth?.model_version ? `Model ${backendHealth.model_version}` : 'Engine Active'}</span>
            </button>

            {/* Live WebSocket Status Pill */}
            <button
              onClick={manualReconnectWS}
              title={wsStatus === 'connected' ? 'WebSocket stream active' : 'Click to reconnect stream'}
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border transition-colors ${
                wsStatus === 'connected'
                  ? 'bg-teal-500/10 text-teal-300 border-teal-500/30'
                  : wsStatus === 'reconnecting'
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/30 animate-pulse'
                  : 'bg-rose-500/10 text-rose-300 border-rose-500/30 hover:bg-rose-500/20 cursor-pointer'
              }`}
            >
              <Radio className={`w-3 h-3 ${wsStatus === 'connected' ? 'animate-pulse text-teal-400' : 'text-slate-400'}`} />
              <span>{wsStatus === 'connected' ? 'Live Stream' : wsStatus === 'reconnecting' ? 'Reconnecting' : 'Stream Offline'}</span>
            </button>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Indian Digital Payment Fraud Engine (UPI • QR • Wallets • IMPS)
          </p>
        </div>
      </div>

      {/* Center: Filters */}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        {/* Channel Selector */}
        <div className="relative">
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            className="bg-[#161F30] border border-slate-700/80 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:border-teal-500 focus:outline-none cursor-pointer"
            aria-label="Filter payment channel"
          >
            <option value="All">All Channels</option>
            <option value="UPI_P2P">UPI P2P</option>
            <option value="UPI_P2M_QR">UPI P2M QR</option>
            <option value="WALLET">Digital Wallet</option>
            <option value="IMPS">IMPS</option>
            <option value="RUPAY_CARD">RuPay Card</option>
          </select>
        </div>

        {/* Time Range */}
        <div className="relative">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="bg-[#161F30] border border-slate-700/80 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:border-teal-500 focus:outline-none cursor-pointer"
            aria-label="Select time range"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>

      {/* Right: Search & Actions */}
      <div className="flex items-center gap-2">
        {/* Search Input */}
        <div className="relative hidden md:block w-44 lg:w-56">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search txn, VPA, ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#161F30] border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-teal-500 focus:outline-none"
          />
        </div>

        {/* Create Alert Button */}
        <button
          onClick={() => setIsCreateAlertOpen(true)}
          className="bg-teal-600 hover:bg-teal-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 shadow-sm transition-all active:scale-95 shrink-0"
        >
          <Plus className="w-3.5 h-3.5 stroke-[3]" />
          <span className="hidden sm:inline">New Alert</span>
        </button>

        {/* Export CSV */}
        <button
          onClick={handleExportCSV}
          title="Export recent transactions to CSV"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          aria-label="Export CSV"
        >
          <Download className="w-4 h-4" />
        </button>

        {/* Notification Bell with Dropdown */}
        <div className="relative">
          <button
            onClick={handleToggleNotif}
            title="Live Alert Notifications"
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors relative"
            aria-label="Open notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 text-white text-[9px] font-black rounded-full flex items-center justify-center ring-2 ring-[#111827]">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Drawer */}
          {isNotifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-[#111827] rounded-xl shadow-2xl border border-slate-800 p-4 z-50 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <h4 className="text-xs font-extrabold text-white">
                    Live Stream Incidents
                  </h4>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">Simulated Feed</span>
                  <button
                    onClick={() => setIsNotifOpen(false)}
                    className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {notifications.length === 0 ? (
                  <p className="text-xs text-slate-500 py-6 text-center">
                    No high-risk transactions detected in current session.
                  </p>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => {
                        setSelectedTransactionId(n.transaction_id);
                        setIsNotifOpen(false);
                      }}
                      className="bg-[#161F30] border border-slate-800 rounded-lg p-2.5 text-xs space-y-1 hover:border-slate-700 transition-colors cursor-pointer"
                    >
                      <div className="flex justify-between items-center font-bold">
                        <span className="font-mono text-teal-400">{n.transaction_id}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          n.decision === 'Block' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {n.decision === 'Block' ? 'Review required' : n.decision} ({n.risk_score})
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-300 text-[11px]">
                        <span>{formatINR(n.amount_inr)}</span>
                        <span className="text-slate-500 font-mono text-[10px]">{n.channel}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate">
                        {n.topReason}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* System Info / Scope Modal Button */}
        <button
          onClick={() => setIsAboutModalOpen(true)}
          title="System Architecture & Limitations"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors"
          aria-label="System info"
        >
          <Info className="w-4 h-4 text-teal-400" />
        </button>
      </div>
    </header>
  );
};
