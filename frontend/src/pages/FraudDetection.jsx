import React, { useState } from 'react';
import {
  ShieldAlert,
  Play,
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  RotateCcw,
} from 'lucide-react';

export const FraudDetection = () => {
  const [formData, setFormData] = useState({
    transaction_id: 'TXN_SIM_' + Math.floor(100000 + Math.random() * 900000),
    card_id: 'CARD_TEST_99',
    customer_id: 'CUST_TEST_99',
    merchant_id: 'MERCH_101',
    merchant_category: 'digital_goods',
    amount: 2.50,
    currency: 'USD',
    country: 'US',
    billing_country: 'RU', // Geo mismatch default
    device_id: 'DEV_NEW_99',
    ip_address: '185.220.101.5',
    is_new_device: 1,
    bin_range: '499999', // High risk BIN
    channel: 'web',
    segment: 'AS Cards',
  });

  const [result, setResult] = useState(null);
  const [scoring, setScoring] = useState(false);

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value,
    }));
  };

  const loadPreset = (type) => {
    if (type === 'card_testing') {
      setFormData((prev) => ({
        ...prev,
        amount: 2.50,
        merchant_category: 'digital_goods',
        country: 'US',
        billing_country: 'RU',
        is_new_device: 1,
        bin_range: '499999',
      }));
    } else if (type === 'velocity') {
      setFormData((prev) => ({
        ...prev,
        amount: 28.50,
        card_id: 'CARD_VEL_88',
        merchant_category: 'gaming',
        country: 'SG',
        billing_country: 'SG',
        is_new_device: 1,
        bin_range: '411111',
      }));
    } else if (type === 'structuring') {
      setFormData((prev) => ({
        ...prev,
        amount: 49.90,
        merchant_category: 'retail',
        country: 'FR',
        billing_country: 'FR',
        is_new_device: 0,
        bin_range: '424242',
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        amount: 14.99,
        country: 'US',
        billing_country: 'US',
        is_new_device: 0,
        bin_range: '411111',
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setScoring(true);
    try {
      const res = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error('Prediction failed:', err);
    } finally {
      setScoring(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-rose-50 text-rose-600 rounded-xl">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-slate-900">Real-Time Fraud Engine Simulator</h2>
            <p className="text-xs text-slate-500 font-medium">
              Score custom transactions live with hybrid XGBoost + Isolation Forest & SHAP
            </p>
          </div>
        </div>

        {/* Preset Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold text-slate-400">Presets:</span>
          <button
            onClick={() => loadPreset('card_testing')}
            className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 transition-colors"
          >
            Card Testing
          </button>
          <button
            onClick={() => loadPreset('velocity')}
            className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded-xl text-xs font-bold border border-amber-200 transition-colors"
          >
            Velocity Attack
          </button>
          <button
            onClick={() => loadPreset('structuring')}
            className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-xl text-xs font-bold border border-purple-200 transition-colors"
          >
            Structuring
          </button>
          <button
            onClick={() => loadPreset('legit')}
            className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-xl text-xs font-bold border border-emerald-200 transition-colors"
          >
            Legitimate Txn
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-6">
          <h3 className="text-base font-bold text-slate-900 mb-4 pb-3 border-b border-gray-100 flex items-center justify-between">
            <span>Transaction Parameters</span>
            <button
              onClick={() =>
                setFormData((prev) => ({
                  ...prev,
                  transaction_id: 'TXN_SIM_' + Math.floor(100000 + Math.random() * 900000),
                }))
              }
              className="text-xs text-[#F97316] font-semibold hover:underline flex items-center gap-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Regenerate ID</span>
            </button>
          </h3>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Transaction Amount ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  name="amount"
                  value={formData.amount}
                  onChange={handleInputChange}
                  className="w-full px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-slate-900 focus:bg-white focus:ring-2 focus:ring-orange-500/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Merchant Category
                </label>
                <select
                  name="merchant_category"
                  value={formData.merchant_category}
                  onChange={handleInputChange}
                  className="w-full px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-slate-800 focus:ring-2 focus:ring-orange-500/30"
                >
                  <option value="digital_goods">digital_goods</option>
                  <option value="retail">retail</option>
                  <option value="gaming">gaming</option>
                  <option value="food_delivery">food_delivery</option>
                  <option value="subscription">subscription</option>
                  <option value="crypto_exchange">crypto_exchange</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Txn Country
                </label>
                <input
                  type="text"
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
                  className="w-full px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs uppercase font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Billing Country
                </label>
                <input
                  type="text"
                  name="billing_country"
                  value={formData.billing_country}
                  onChange={handleInputChange}
                  className="w-full px-3.5 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs uppercase font-bold text-slate-900"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Card ID
                </label>
                <input
                  type="text"
                  name="card_id"
                  value={formData.card_id}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  BIN Range
                </label>
                <input
                  type="text"
                  name="bin_range"
                  value={formData.bin_range}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Is New Device?
                </label>
                <select
                  name="is_new_device"
                  value={formData.is_new_device}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      is_new_device: parseInt(e.target.value),
                    }))
                  }
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold"
                >
                  <option value={1}>Yes (1)</option>
                  <option value={0}>No (0)</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={scoring}
              className="w-full py-3 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl text-sm font-bold shadow-lg transition-all flex items-center justify-center gap-2 transform active:scale-98"
            >
              <Zap className={`w-4 h-4 ${scoring ? 'animate-bounce' : ''}`} />
              <span>{scoring ? 'Evaluating ML Models...' : 'Run Real-Time Scoring'}</span>
            </button>
          </form>
        </div>

        {/* Right Output Results Panel (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-6 flex flex-col justify-between">
          {!result ? (
            <div className="h-full flex flex-col items-center justify-center py-12 text-center text-slate-400">
              <Cpu className="w-12 h-12 text-slate-300 mb-3 animate-pulse" />
              <p className="text-sm font-bold text-slate-700">Awaiting Simulation Input</p>
              <p className="text-xs text-slate-400 max-w-xs mt-1">
                Configure parameters on the left or select a scenario preset to run live inference.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Risk Score Dial Meter */}
              <div className="text-center pt-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Risk Score Assessment
                </span>

                <div className="relative my-4 flex justify-center">
                  <div className="w-40 h-40 rounded-full border-[10px] border-slate-100 flex flex-col items-center justify-center shadow-inner relative">
                    <span
                      className={`text-4xl font-extrabold tracking-tight ${
                        result.risk_score > 70
                          ? 'text-rose-600'
                          : result.risk_score > 40
                          ? 'text-amber-600'
                          : 'text-emerald-600'
                      }`}
                    >
                      {result.risk_score}
                    </span>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">
                      out of 100
                    </span>
                  </div>
                </div>

                {/* Decision Badge */}
                <div className="flex justify-center">
                  <span
                    className={`inline-flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-extrabold border shadow-sm ${
                      result.decision === 'Block'
                        ? 'bg-rose-100 text-rose-700 border-rose-300'
                        : result.decision === 'Manual Review'
                        ? 'bg-amber-100 text-amber-700 border-amber-300'
                        : 'bg-emerald-100 text-emerald-700 border-emerald-300'
                    }`}
                  >
                    {result.decision === 'Block' && <XCircle className="w-4 h-4" />}
                    {result.decision === 'Manual Review' && <AlertTriangle className="w-4 h-4" />}
                    {result.decision === 'Allow' && <CheckCircle2 className="w-4 h-4" />}
                    <span>Decision: {result.decision}</span>
                  </span>
                </div>
              </div>

              {/* Probabilities Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <p className="text-slate-400 font-medium">XGBoost Fraud Prob</p>
                  <p className="text-sm font-extrabold text-slate-900 mt-0.5">
                    {(result.xgb_probability * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <p className="text-slate-400 font-medium">Isolation Anomaly</p>
                  <p className="text-sm font-extrabold text-slate-900 mt-0.5">
                    {(result.anomaly_score * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* Top 3 SHAP Reasons */}
              <div className="space-y-2 pt-2 border-t border-gray-100">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Top 3 Key Risk Reasons (SHAP)
                </h4>
                <div className="space-y-2">
                  {result.reasons.map((reason, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2.5 bg-gray-50 border border-gray-200 p-2.5 rounded-xl text-xs font-semibold text-slate-800"
                    >
                      <span className="w-5 h-5 rounded-full bg-[#1B212C] text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                        {idx + 1}
                      </span>
                      <span>{reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
