import React, { useState, useEffect } from 'react';
import { Store, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const Merchants = () => {
  const { searchQuery } = useFilter();

  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [page, setPage] = useState(1);

  const fetchMerchants = async () => {
    setLoading(true);
    try {
      let url = `http://localhost:8000/api/merchants?page=${page}&limit=20`;
      if (categoryFilter !== 'All') url += `&category=${encodeURIComponent(categoryFilter)}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();
      setMerchants(data);
    } catch (err) {
      console.error('Failed to fetch merchants:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMerchants();
  }, [page, categoryFilter, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
            <Store className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Merchant Volume Anomalies</h2>
            <p className="text-xs text-slate-500">Volume spike ratio and merchant category monitoring</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700"
          >
            <option value="All">All Categories</option>
            <option value="digital_goods">digital_goods</option>
            <option value="retail">retail</option>
            <option value="gaming">gaming</option>
            <option value="food_delivery">food_delivery</option>
            <option value="subscription">subscription</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <div className="overflow-x-auto rounded-xl border border-gray-200/80">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#E5E9F2] text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-gray-200">
                <th className="py-3 px-4">Merchant ID</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-center">Spike Ratio</th>
                <th className="py-3 px-4">Risk Level</th>
                <th className="py-3 px-4 text-center">Txn Count</th>
                <th className="py-3 px-4 text-right">Total Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-700 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-400">
                    Loading merchant profiles...
                  </td>
                </tr>
              ) : merchants.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-400">
                    No merchants match current criteria.
                  </td>
                </tr>
              ) : (
                merchants.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {m.merchant_id}
                    </td>
                    <td className="py-3.5 px-4 capitalize font-semibold">{m.category}</td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 font-mono font-extrabold px-2.5 py-0.5 rounded text-xs ${
                          m.spike_ratio > 3.0
                            ? 'bg-rose-100 text-rose-700 border border-rose-300'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {m.spike_ratio > 3.0 && <AlertTriangle className="w-3 h-3 text-rose-600" />}
                        <span>{m.spike_ratio.toFixed(1)}x</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-[11px] font-bold border ${
                          m.risk_level === 'High'
                            ? 'bg-rose-50 text-rose-600 border-rose-200'
                            : m.risk_level === 'Medium'
                            ? 'bg-amber-50 text-amber-600 border-amber-200'
                            : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                        }`}
                      >
                        {m.risk_level}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold">
                      {m.transaction_count}
                    </td>
                    <td className="py-3.5 px-4 text-right font-extrabold text-slate-900">
                      ${m.total_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between pt-4">
          <p className="text-xs text-slate-500">
            Showing Page <strong>{page}</strong>
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="p-2 border border-gray-200 rounded-xl hover:bg-gray-100 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage(page + 1)}
              className="p-2 border border-gray-200 rounded-xl hover:bg-gray-100"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
