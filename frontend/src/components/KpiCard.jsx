import React from 'react';

export const KpiCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  badge,
  badgeType = 'neutral',
  accentColor = 'teal',
  loading = false,
  tooltip,
}) => {
  const getAccent = () => {
    switch (accentColor) {
      case 'rose':
        return 'text-rose-700 bg-rose-50 border-rose-200';
      case 'amber':
        return 'text-amber-800 bg-amber-50 border-amber-200';
      case 'emerald':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'blue':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      default:
        return 'text-teal-800 bg-teal-50 border-teal-200';
    }
  };

  const getBadgeStyle = () => {
    switch (badgeType) {
      case 'danger':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'warning':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'success':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <div title={tooltip} className="bg-[#111827] border border-slate-800/80 rounded-lg p-4 shadow-card-soft transition-colors flex flex-col justify-between">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-xs font-medium text-slate-400 tracking-wide block">
            {title}
          </span>
          {loading ? (
            <div className="h-7 w-24 bg-slate-100 rounded animate-pulse my-1.5" />
          ) : (
            <div className="text-2xl font-extrabold text-white tracking-tight my-0.5">
              {value}
            </div>
          )}
        </div>

        {Icon && (
          <div className={`p-2 rounded-lg border ${getAccent()} shrink-0`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs mt-3 pt-2.5 border-t border-slate-800/60">
        <span className="text-slate-400 text-[11px] truncate">
          {subtitle}
        </span>
        {badge && (
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getBadgeStyle()} shrink-0 ml-2`}>
            {badge}
          </span>
        )}
      </div>
    </div>
  );
};
