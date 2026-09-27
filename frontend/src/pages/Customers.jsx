import React, { useState, useEffect } from 'react';
import { Users, Search, ChevronLeft, ChevronRight, ShieldAlert } from 'lucide-react';
import { useFilter } from '../context/FilterContext';

export const Customers = () => {
  const { searchQuery, setSearchQuery } = useFilter();

  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState('All');
  const [page, setPage] = useState(1);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      let url = `http://localhost:8000/api/customers?page=${page}&limit=20`;
      if (riskFilter !== 'All') url += `&risk_level=${encodeURIComponent(riskFilter)}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();
      setCustomers(data);
    } catch (err) {
      console.error('Failed to fetch customers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, [page, riskFilter, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Customer Risk Profiles</h2>
            <p className="text-xs text-slate-500">Account risk levels and fraud incident history</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-700"
          >
            <option value="All">All Risk Levels</option>
            <option value="Low">Low Risk</option>
            <option value="Medium">Medium Risk</option>
            <option value="High">High Risk</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <div className="overflow-x-auto rounded-xl border border-gray-200/80">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#E5E9F2] text-slate-700 text-[11px] font-bold uppercase tracking-wider border-b border-gray-200">
                <th className="py-3 px-4">Customer ID</th>
                <th className="py-3 px-4">Segment</th>
                <th className="py-3 px-4">Risk Level</th>
                <th className="py-3 px-4 text-center">Total Txns</th>
                <th className="py-3 px-4 text-center">Fraud Incidents</th>
                <th className="py-3 px-4 text-right">Total Spend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-700 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-400">
                    Loading customer profiles...
                  </td>
                </tr>
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-400">
                    No customers found matching criteria.
                  </td>
                </tr>
              ) : (
                customers.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                      {c.customer_id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold">{c.segment}</td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-[11px] font-bold border ${
                          c.risk_level === 'High'
                            ? 'bg-rose-50 text-rose-600 border-rose-200'
                            : c.risk_level === 'Medium'
                            ? 'bg-amber-50 text-amber-600 border-amber-200'
                            : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                        }`}
                      >
                        {c.risk_level} Risk
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold">
                      {c.total_transactions}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`font-mono font-bold ${
                          c.fraud_incidents > 0 ? 'text-rose-600' : 'text-slate-400'
                        }`}
                      >
                        {c.fraud_incidents}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-extrabold text-slate-900">
                      ${c.total_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
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
