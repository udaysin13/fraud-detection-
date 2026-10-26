import React, { useState } from 'react';
import {
  ShieldAlert,
  Play,
  RotateCcw,
  Cpu,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  AlertCircle,
  HelpCircle,
  Layers,
  Activity,
  Zap,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { formatINR, getRiskStyle } from '../utils/formatters';

const PRESETS = {
  sim_swap_ato: {
    label: 'SIM Swap + Device Takeover (High Risk)',
    description: 'Critical account takeover signature: First-time beneficiary with simultaneous SIM swap & unfamiliar device.',
    data: {
      amount_inr: 8500.0,
      channel: 'UPI_P2P',
      transaction_type: 'P2P_TRANSFER',
      sender_id: 'CUST_IND_9099',
      sender_vpa: 'victim.user@okhdfcbank',
      beneficiary_id: 'BEN_IND_MULE_101',
      beneficiary_vpa: 'mule.drain@paytm',
      merchant_id: 'NOT_APPLICABLE',
      merchant_category: 'p2p_transfer',
      device_id: 'DEV_NEW_ATO_99',
      is_new_device: 1,
      sim_change_flag: 1,
      ip_location_state: 'Maharashtra',
    },
  },
  mule_micro_testing: {
    label: 'Mule QR Micro-Testing Probe (High Risk)',
    description: 'Rapid low-value probe testing payment instrument validity on merchant terminal before larger drain.',
    data: {
      amount_inr: 2.5,
      channel: 'UPI_P2M_QR',
      transaction_type: 'QR_PAYMENT',
      sender_id: 'CUST_IND_4412',
      sender_vpa: 'test.probe@okaxis',
      beneficiary_id: 'MERCH_IND_112',
      beneficiary_vpa: 'croma.retail@hdfcbank',
      merchant_id: 'MERCH_IND_112',
      merchant_category: 'digital_services',
      device_id: 'DEV_IND_PROBE_01',
      is_new_device: 1,
      sim_change_flag: 0,
      ip_location_state: 'Delhi',
    },
  },
  structuring_probe: {
    label: 'Regulatory Structuring Probe (Review)',
    description: 'Amount ₹4,990 structured just under the ₹5,000 regulatory surveillance ceiling.',
    data: {
      amount_inr: 4990.0,
      channel: 'IMPS',
      transaction_type: 'P2P_TRANSFER',
      sender_id: 'CUST_IND_3029',
      sender_vpa: 'rahul.nair50@barodampay',
      beneficiary_id: 'BEN_IND_1610',
      beneficiary_vpa: 'karthik.gupta17@okhdfcbank',
      merchant_id: 'NOT_APPLICABLE',
      merchant_category: 'p2p_transfer',
      device_id: 'DEV_IND_12029',
      is_new_device: 0,
      sim_change_flag: 0,
      ip_location_state: 'Gujarat',
    },
  },
  legit_kirana: {
    label: 'Verified Kirana Merchant Payment (Low Risk)',
    description: 'Standard grocery QR payment from established customer device with normal velocity baseline.',
    data: {
      amount_inr: 185.0,
      channel: 'UPI_P2M_QR',
      transaction_type: 'MERCHANT_PAYMENT',
      sender_id: 'CUST_IND_1464',
      sender_vpa: 'sanjay.sharma69@paytm',
      beneficiary_id: 'MERCH_IND_102',
      beneficiary_vpa: 'apna.kirana@paytm',
      merchant_id: 'MERCH_IND_102',
      merchant_category: 'kirana_grocery',
      device_id: 'DEV_IND_10464',
      is_new_device: 0,
      sim_change_flag: 0,
      ip_location_state: 'Rajasthan',
    },
  },
};

export const FraudDetection = () => {
  const [formData, setFormData] = useState({
    transaction_id: 'TXN_TEST_' + Math.floor(100000 + Math.random() * 900000),
    amount_inr: 8500.0,
    channel: 'UPI_P2P',
    transaction_type: 'P2P_TRANSFER',
    sender_id: 'CUST_IND_9099',
    sender_vpa: 'victim.user@okhdfcbank',
    beneficiary_id: 'BEN_IND_MULE_101',
    beneficiary_vpa: 'mule.drain@paytm',
    merchant_id: 'NOT_APPLICABLE',
    merchant_category: 'p2p_transfer',
    device_id: 'DEV_NEW_ATO_99',
    is_new_device: 1,
    sim_change_flag: 1,
    ip_location_state: 'Maharashtra',
  });

  const [scoring, setScoring] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activePresetKey, setActivePresetKey] = useState('sim_swap_ato');

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value,
    }));
  };

  const loadPreset = (presetKey) => {
    const preset = PRESETS[presetKey];
    if (preset) {
      setActivePresetKey(presetKey);
      setFormData((prev) => ({
        ...prev,
        ...preset.data,
        transaction_id: 'TXN_TEST_' + Math.floor(100000 + Math.random() * 900000),
      }));
    }
  };

  const regenerateTxnId = () => {
    setFormData((prev) => ({
      ...prev,
      transaction_id: 'TXN_TEST_' + Math.floor(100000 + Math.random() * 900000),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Client-side validation
    if (formData.amount_inr <= 0) {
      setError('Transaction amount must be a positive number.');
      return;
    }

    setScoring(true);
    setError(null);

    try {
      const response = await apiClient.predictTransaction(formData);
      setResult(response);
    } catch (err) {
      console.error('Inference error:', err);
      setError(err.message || 'Scoring engine returned an error.');
    } finally {
      setScoring(false);
    }
  };

  const riskStyle = result ? getRiskStyle(result.decision, result.risk_score) : null;

  return (
    <div className="space-y-6">
      {/* Header Strip */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-600 rounded-xl">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Transaction Risk Simulator</h2>
            <p className="text-xs text-slate-400">
              Sends a sample transaction to the configured model API. Predictions are estimates and may be incorrect.
            </p>
          </div>
        </div>

        {/* Preset Selectors */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold text-slate-400">Test Scenarios:</span>
          {Object.entries(PRESETS).map(([key, p]) => (
            <button
              key={key}
              type="button"
              onClick={() => loadPreset(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                activePresetKey === key
                  ? 'bg-teal-600 text-slate-800 border-teal-500 shadow-sm'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-600 hover:text-slate-800'
              }`}
            >
              {key === 'sim_swap_ato'
                ? 'SIM Swap Takeover'
                : key === 'mule_micro_testing'
                ? 'Micro-Testing Probe'
                : key === 'structuring_probe'
                ? 'Structuring'
                : 'Legitimate Kirana'}
            </button>
          ))}
        </div>
      </div>

      {/* Preset Context Banner */}
      {activePresetKey && PRESETS[activePresetKey] && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-600 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-600 shrink-0" />
            <span>
              <strong>Active Scenario:</strong> {PRESETS[activePresetKey].description}
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-500 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Form & Results Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form Column (7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 shadow-card-soft">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-5">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <span>Transaction Parameters (Indian UPI Schema)</span>
            </h3>
            <button
              onClick={regenerateTxnId}
              className="text-xs text-teal-600 hover:text-teal-600 font-bold flex items-center gap-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Regenerate ID</span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Transaction Amount (INR ₹)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  name="amount_inr"
                  value={formData.amount_inr}
                  onChange={handleInputChange}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold text-slate-800 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Payment Channel
                </label>
                <select
                  name="channel"
                  value={formData.channel}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value="UPI_P2P">UPI P2P Transfer</option>
                  <option value="UPI_P2M_QR">UPI P2M QR Merchant</option>
                  <option value="WALLET">Digital Wallet</option>
                  <option value="IMPS">IMPS Immediate Payment</option>
                  <option value="RUPAY_CARD">RuPay Card</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Transaction Type
                </label>
                <select
                  name="transaction_type"
                  value={formData.transaction_type}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value="P2P_TRANSFER">P2P_TRANSFER</option>
                  <option value="QR_PAYMENT">QR_PAYMENT</option>
                  <option value="MERCHANT_PAYMENT">MERCHANT_PAYMENT</option>
                  <option value="COLLECT_REQUEST">COLLECT_REQUEST (High Phishing Risk)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Merchant Category
                </label>
                <select
                  name="merchant_category"
                  value={formData.merchant_category}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value="p2p_transfer">p2p_transfer</option>
                  <option value="kirana_grocery">kirana_grocery</option>
                  <option value="food_dining">food_dining</option>
                  <option value="digital_services">digital_services</option>
                  <option value="transport_travel">transport_travel</option>
                  <option value="retail_fashion">retail_fashion</option>
                  <option value="pharmacy_health">pharmacy_health</option>
                  <option value="electronics">electronics</option>
                  <option value="gaming_entertainment">gaming_entertainment</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Sender UPI VPA / Account
                </label>
                <input
                  type="text"
                  required
                  name="sender_vpa"
                  value={formData.sender_vpa}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Beneficiary UPI VPA
                </label>
                <input
                  type="text"
                  required
                  name="beneficiary_vpa"
                  value={formData.beneficiary_vpa}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800 focus:outline-none focus:border-teal-500"
                />
              </div>
            </div>

            {/* Account Takeover Signals Section */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Account Takeover (ATO) & Device Telemetry
              </span>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    New Device?
                  </label>
                  <select
                    name="is_new_device"
                    value={formData.is_new_device}
                    onChange={(e) =>
                      setFormData((p) => ({ ...p, is_new_device: parseInt(e.target.value) }))
                    }
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-teal-500"
                  >
                    <option value={0}>No (Recognized)</option>
                    <option value={1}>Yes (Unfamiliar Device)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    SIM Card Change?
                  </label>
                  <select
                    name="sim_change_flag"
                    value={formData.sim_change_flag}
                    onChange={(e) =>
                      setFormData((p) => ({ ...p, sim_change_flag: parseInt(e.target.value) }))
                    }
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-teal-500"
                  >
                    <option value={0}>No (Standard SIM)</option>
                    <option value={1}>Yes (Recent SIM Swap)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Region / State
                  </label>
                  <select
                    name="ip_location_state"
                    value={formData.ip_location_state}
                    onChange={handleInputChange}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:border-teal-500"
                  >
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Delhi">Delhi</option>
                    <option value="Karnataka">Karnataka</option>
                    <option value="Gujarat">Gujarat</option>
                    <option value="Uttar Pradesh">Uttar Pradesh</option>
                    <option value="Tamil Nadu">Tamil Nadu</option>
                    <option value="West Bengal">West Bengal</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Submit Action */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={scoring}
                className="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-slate-800 rounded-lg text-xs font-bold transition-all shadow-md flex items-center justify-center gap-2"
              >
                {scoring ? (
                  <>
                    <RotateCcw className="w-4 h-4 animate-spin" />
                    <span>Scoring Payload against Historical Baselines...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Analyze transaction</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right Output Column (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 shadow-card-soft flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-200 mb-4">
              <h3 className="text-sm font-bold text-slate-800">Model result</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Risk score and explanation text returned by the prediction API
              </p>
            </div>

            {!result ? (
              <div className="py-20 text-center text-xs text-slate-500 space-y-2">
                <Cpu className="w-10 h-10 mx-auto opacity-30 text-teal-600 mb-2" />
                <p className="font-semibold text-slate-400">Engine Standing By</p>
                <p className="text-slate-500 max-w-xs mx-auto">
                  Configure payment parameters on the left or click a scenario preset to run live inference.
                </p>
              </div>
            ) : (
              <div className="space-y-5 animate-in fade-in duration-300">
                {/* Risk Score Dial Meter */}
                <div className="text-center pt-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-3">
                    Estimated risk score (0–100)
                  </span>

                  <div className="relative inline-flex items-center justify-center">
                    <div className="w-36 h-36 rounded-full border-8 border-slate-200 flex flex-col items-center justify-center shadow-inner relative">
                      <span className={`text-4xl font-extrabold tracking-tight ${riskStyle.text}`}>
                        {result.risk_score}
                      </span>
                      <span className="text-[10px] font-bold text-slate-400 uppercase mt-0.5">
                        out of 100
                      </span>
                    </div>
                  </div>

                  {/* Decision Badge */}
                  <div className="mt-4 flex justify-center">
                    <span className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold border shadow-sm ${riskStyle.bg} ${riskStyle.border} ${riskStyle.text}`}>
                      {result.decision === 'Block' && <XCircle className="w-4 h-4" />}
                      {result.decision === 'Manual Review' && <AlertTriangle className="w-4 h-4" />}
                      {result.decision === 'Allow' && <CheckCircle2 className="w-4 h-4" />}
                      <span>Recommended action: {result.recommended_action || result.decision}</span>
                    </span>
                  </div>
                </div>

                {/* Probabilities Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium text-[11px]">XGBoost probability</p>
                    <p className="text-base font-extrabold text-slate-800 mt-0.5">
                      {result.xgb_probability != null || result.fraud_probability != null
                        ? `${((result.xgb_probability ?? result.fraud_probability) * 100).toFixed(1)}%`
                        : 'Unavailable'}
                    </p>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium text-[11px]">Isolation anomaly score</p>
                    <p className="text-base font-extrabold text-slate-800 mt-0.5">
                      {result.anomaly_score != null ? `${(result.anomaly_score * 100).toFixed(1)}%` : 'Unavailable'}
                    </p>
                  </div>
                </div>

                {/* Explanations returned by the scoring service */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 space-y-2">
                  <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-amber-600" />
                    Model-provided reasons
                  </h4>

                  <ul className="space-y-1.5 text-xs">
                    {result.reasons && result.reasons.length > 0 ? (
                      result.reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-slate-600 bg-white p-2 rounded border border-slate-200">
                          <span className="w-4 h-4 rounded-full bg-slate-100 text-teal-600 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                            {idx + 1}
                          </span>
                          <span className="text-[11px]">{reason}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-500 italic text-xs">No explanatory signals found.</li>
                    )}
                  </ul>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3.5 space-y-2">
                  <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" /> Rule signals (separate from ML score)
                  </h4>
                  {result.rule_signals?.length ? <ul className="space-y-1.5 text-xs">{result.rule_signals.map((signal) => (
                    <li key={signal.rule_id} className="bg-white border border-blue-100 rounded p-2 text-slate-700">
                      <span className="font-bold mr-1">{signal.severity}:</span>{signal.message}
                    </li>
                  ))}</ul> : <p className="text-xs text-slate-600">No configured rules fired for the available transaction context.</p>}
                </div>

                {/* System Meta */}
                <p className="text-[11px] text-slate-500">Model explanations and transparent rule signals are shown separately. Neither is proof of fraud.</p>

                <div className="text-[10px] text-slate-500 border-t border-slate-200 pt-2 flex justify-between">
                  <span>Engine: {result.model_version || 'v1.0.0-xgb-iso'}</span>
                  <span>Category: {result.risk_category}</span>
                </div>
              </div>
            )}
          </div>

          {/* Academic & Decision-Support Disclaimer */}
          <div className="pt-4 border-t border-slate-200 text-[10px] text-slate-500 flex items-start gap-2">
            <HelpCircle className="w-4 h-4 text-slate-600 shrink-0 mt-0.5" />
            <p>
              <strong>Decision-support only</strong>: this prototype does not authorize, block, or process payments. Review the transaction independently; model predictions can be wrong.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
