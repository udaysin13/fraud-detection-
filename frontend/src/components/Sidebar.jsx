import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  CreditCard,
  ShieldAlert,
  FileSearch,
  Users,
  Store,
  Sliders,
  Bell,
  FileBarChart,
  CheckSquare,
  Lock,
  X,
  Info,
} from 'lucide-react';
import { useFilter } from '../context/FilterContext';

const MENU_ITEMS = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Transactions', path: '/transactions', icon: CreditCard },
  { name: 'Fraud Analysis', path: '/fraud-detection', icon: ShieldAlert },
  { name: 'Alerts', path: '/alerts', icon: Bell },
  { name: 'Investigations', path: '/investigations', icon: FileSearch },
  { name: 'Model Insights', path: '/rules-models', icon: Sliders },
];

const SUPPORT_ITEMS = [
  { name: 'Customers', path: '/customers', icon: Users },
  { name: 'Merchants', path: '/merchants', icon: Store },
  { name: 'Reports', path: '/reports', icon: FileBarChart },
  { name: 'Compliance', path: '/compliance', icon: CheckSquare },
  { name: 'Administration', path: '/admin', icon: Lock },
];

export const Sidebar = ({ isMobileOpen, onCloseMobile }) => {
  const { backendHealth, setIsAboutModalOpen } = useFilter();

  const sidebarContent = (
    <aside
      className="bg-white text-slate-600 rounded-lg p-3 flex flex-col gap-5 border border-slate-200 shadow-card-soft h-full w-60"
    >
      <div className="space-y-5">
        {/* Sidebar Header */}
        <div
          className="flex items-center justify-between px-1 pb-3 border-b border-slate-200"
        >
          <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Workspace</span>

          {/* Mobile Close Button */}
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100"
              aria-label="Close navigation"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1" aria-label="Main navigation">
          {MENU_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-[#E8F6F3] text-[#0F766E] border-l-2 border-[#0F766E]'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span className="truncate">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-slate-200 pt-4">
          <p className="px-3 pb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">Workspace tools</p>
          {SUPPORT_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={onCloseMobile}
                className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${isActive ? 'bg-[#EFF6FF] text-[#2563EB]' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'}`}
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
          <button
            type="button"
            onClick={() => { setIsAboutModalOpen(true); onCloseMobile?.(); }}
            className="flex w-full items-center gap-3 px-3 py-2 rounded-md text-xs font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-50"
          >
            <Info className="w-4 h-4" aria-hidden="true" />
            About VaultGuard
          </button>
        </div>
      </div>

      {/* Footer Status Pill */}
      <div className="mt-auto pt-3 border-t border-slate-200">
          <div className="bg-slate-50 rounded-md p-2.5 flex items-center gap-2.5 border border-slate-200">
            <div className={`w-2 h-2 rounded-full shrink-0 ${backendHealth?.status === 'healthy' ? 'bg-emerald-600' : 'bg-amber-500'}`}></div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold text-slate-700 truncate">API {backendHealth?.status || 'status unknown'}</p>
              <p className="text-[10px] text-slate-500 truncate">
                {backendHealth?.model_version || 'Model status unavailable'}
              </p>
            </div>
          </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="hidden lg:block shrink-0">
        {sidebarContent}
      </div>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 w-64 h-full p-3 bg-[#F5F8FC]">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
