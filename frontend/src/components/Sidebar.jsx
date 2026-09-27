import React, { useState } from 'react';
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
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

const MENU_ITEMS = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Transactions', path: '/transactions', icon: CreditCard },
  { name: 'Fraud Detection', path: '/fraud-detection', icon: ShieldAlert },
  { name: 'Investigations', path: '/investigations', icon: FileSearch },
  { name: 'Customers', path: '/customers', icon: Users },
  { name: 'Merchants', path: '/merchants', icon: Store },
  { name: 'Rules & Models', path: '/rules-models', icon: Sliders },
  { name: 'Alerts', path: '/alerts', icon: Bell },
  { name: 'Reports', path: '/reports', icon: FileBarChart },
  { name: 'Compliance', path: '/compliance', icon: CheckSquare },
  { name: 'Admin Panel', path: '/admin', icon: Lock },
];

export const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={`bg-[#1B212C] text-slate-300 rounded-[16px] p-4 flex flex-col justify-between transition-all duration-300 shadow-xl border border-slate-800 ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Upper Navigation Links */}
      <div className="space-y-6">
        {/* Toggle Collapse Header */}
        <div
          className={`flex items-center justify-between pb-3 border-b border-slate-800/80 ${
            isCollapsed ? 'justify-center' : 'px-2'
          }`}
        >
          {!isCollapsed && (
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Navigation
            </span>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors flex items-center justify-center"
            title={isCollapsed ? 'Expand Sidebar' : 'Hide Panel'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-[#F97316]" />
            ) : (
              <div className="flex items-center gap-1 text-[11px] font-semibold">
                <ChevronLeft className="w-4 h-4 text-[#F97316]" />
                <span>Hide Panel</span>
              </div>
            )}
          </button>
        </div>

        {/* Nav Links */}
        <nav className="space-y-1.5">
          {MENU_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3.5 px-3 py-2.5 rounded-xl font-medium text-xs transition-all ${
                    isActive
                      ? 'bg-[#F97316] text-white font-bold shadow-md shadow-orange-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`
                }
                title={isCollapsed ? item.name : undefined}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!isCollapsed && <span className="truncate">{item.name}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Status Badge */}
      <div className="pt-4 border-t border-slate-800/80">
        {!isCollapsed ? (
          <div className="bg-slate-800/50 rounded-xl p-3 flex items-center gap-3 border border-slate-700/50">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></div>
            <div>
              <p className="text-[11px] font-bold text-white">Engine Live</p>
              <p className="text-[10px] text-slate-400">v1.0.0 Hybrid Engine</p>
            </div>
          </div>
        ) : (
          <div
            className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse mx-auto"
            title="Engine Live"
          ></div>
        )}
      </div>
    </aside>
  );
};
