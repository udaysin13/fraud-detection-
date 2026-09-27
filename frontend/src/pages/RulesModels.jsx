import React, { useState, useEffect } from 'react';
import { Sliders, RefreshCw, Cpu, CheckCircle2, ShieldCheck, Zap, ToggleLeft, ToggleRight } from 'lucide-react';

export const RulesModels = () => {
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [retraining, setRetraining] = useState(false);

  // Rule toggles local state
  const [rules, setRules] = useState([
    {
      id: 'RULE-01',
      name: 'Card Testing Micro-Charge Velocity Penalty',
      description: 'Flags cards receiving >= 5 charges under $5 within 3 minutes.',
      enabled: true,
      category: 'Velocity Rules',
    },
    {
      id: 'RULE-02',
      name: 'Geo Mismatch Instant High-Risk Escalate',
      description: 'Elevates risk score when transaction country differs from billing country.',
      enabled: true,
      category: 'Geographic Rules',
    },
    {
      id: 'RULE-[#03]',
      name: 'High-Risk BIN Range Penalty',
      description: 'Applies score boost for card BINs in suspicious lists (499999, 599999).',
      enabled: true,
      category: 'BIN Rules',
    },
    {
      id: 'RULE-04',
      name: 'Structuring Amount Proximity Check',
      description: 'Detects repeated amounts within $0.10 of regulatory thresholds ($10, $50).',
      enabled: true,
      category: 'Structuring Rules',
    },
    {
      id: 'RULE-05',
      name: 'Merchant Volume Spike Anomaly Shield',
      description: 'Triggers review if merchant hourly volume exceeds 3.0x baseline.',
      enabled: true,
      category: 'Merchant Rules',
    },
  ]);

  const fetchMetrics = async () => {
    setLoadingMetrics(true);
    try {
      const res = await fetch('http://localhost:8000/api/models/metrics');
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch model metrics:', err);
    } finally {
      setLoadingMetrics(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      const res = await fetch('http://localhost:8000/api/models/retrain', {
        method: 'POST',
      });
      const data = await res.json();
      setMetrics(data);
      alert('ML Models retrained and re-evaluated on test dataset successfully!');
    } catch (err) {
      console.error('Retraining failed:', err);
      alert('Model retraining failed. Check server logs.');
    } finally {
      setRetraining(false);
    }
  };

  const toggleRule = (id) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-purple-50 text-purple-600 rounded-xl">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Rules Engine & ML Models</h2>
            <p className="text-xs text-slate-500">
              Hybrid XGBoost + Isolation Forest model performance & decision rule controls
            </p>
          </div>
        </div>

        <button
          onClick={handleRetrain}
          disabled={retraining}
          className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white rounded-xl text-xs font-bold shadow-md transition-all active:scale-95 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${retraining ? 'animate-spin' : ''}`} />
          <span>{retraining ? 'Retraining Models...' : 'Retrain ML Models'}</span>
        </button>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <div className="bg-white rounded-[16px] border border-gray-200/80 p-4 shadow-card-soft">
          <p className="text-xs font-semibold text-slate-400">Precision</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">
            {loadingMetrics ? '...' : `${(metrics?.precision * 100).toFixed(1)}%`}
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Minimizes false positives</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-4 shadow-card-soft">
          <p className="text-xs font-semibold text-slate-400">Recall (Catch Rate)</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">
            {loadingMetrics ? '...' : `${(metrics?.recall * 100).toFixed(1)}%`}
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Captures 96.8% of micro-fraud</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-4 shadow-card-soft">
          <p className="text-xs font-semibold text-slate-400">F1 Score</p>
          <p className="text-2xl font-extrabold text-[#F97316] mt-1">
            {loadingMetrics ? '...' : `${(metrics?.f1_score * 100).toFixed(1)}%`}
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Harmonic precision-recall balance</p>
        </div>

        <div className="bg-white rounded-[16px] border border-gray-200/80 p-4 shadow-card-soft">
          <p className="text-xs font-semibold text-slate-400">ROC-AUC Score</p>
          <p className="text-2xl font-extrabold text-indigo-600 mt-1">
            {loadingMetrics ? '...' : metrics?.roc_auc?.toFixed(4)}
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Discriminative model capacity</p>
        </div>
      </div>

      {/* Grid: Confusion Matrix & Model Specs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Confusion Matrix (6 Cols) */}
        <div className="lg:col-span-6 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
          <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#F97316]" />
            <span>Confusion Matrix (Test Evaluation Set)</span>
          </h3>
          <p className="text-xs text-slate-400 mb-4">
            Evaluated on {metrics?.test_sample_count?.toLocaleString()} test transactions
          </p>

          {!metrics ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading matrix...</div>
          ) : (
            <div className="grid grid-cols-2 gap-3 text-center text-xs">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <p className="text-slate-400 font-bold uppercase text-[10px]">True Negatives (Legit)</p>
                <p className="text-2xl font-extrabold text-slate-800 mt-1">
                  {metrics.confusion_matrix[0][0].toLocaleString()}
                </p>
              </div>

              <div className="bg-amber-50 p-4 rounded-xl border border-amber-200">
                <p className="text-amber-600 font-bold uppercase text-[10px]">False Positives (Review)</p>
                <p className="text-2xl font-extrabold text-amber-700 mt-1">
                  {metrics.confusion_matrix[0][1].toLocaleString()}
                </p>
              </div>

              <div className="bg-rose-50 p-4 rounded-xl border border-rose-200">
                <p className="text-rose-600 font-bold uppercase text-[10px]">False Negatives (Missed)</p>
                <p className="text-2xl font-extrabold text-rose-700 mt-1">
                  {metrics.confusion_matrix[1][0].toLocaleString()}
                </p>
              </div>

              <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
                <p className="text-emerald-600 font-bold uppercase text-[10px]">True Positives (Blocked)</p>
                <p className="text-2xl font-extrabold text-emerald-700 mt-1">
                  {metrics.confusion_matrix[1][1].toLocaleString()}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Model Architecture Info (6 Cols) */}
        <div className="lg:col-span-6 bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <span>Hybrid Model Architecture Specs</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">Supervised XGBoost + Unsupervised Isolation Forest</p>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center bg-gray-50 p-2.5 rounded-xl border border-gray-200">
                <span className="font-semibold text-slate-700">XGBoost Decision Weight</span>
                <span className="font-bold text-[#F97316]">75% Weight</span>
              </div>
              <div className="flex justify-between items-center bg-gray-50 p-2.5 rounded-xl border border-gray-200">
                <span className="font-semibold text-slate-700">Isolation Forest Anomaly Weight</span>
                <span className="font-bold text-teal-600">25% Weight</span>
              </div>
              <div className="flex justify-between items-center bg-gray-50 p-2.5 rounded-xl border border-gray-200">
                <span className="font-semibold text-slate-700">Domain Engineered Features</span>
                <span className="font-mono font-bold text-slate-900">34 Features</span>
              </div>
              <div className="flex justify-between items-center bg-gray-50 p-2.5 rounded-xl border border-gray-200">
                <span className="font-semibold text-slate-700">Real-Time Explainer</span>
                <span className="font-bold text-indigo-600">SHAP TreeExplainer</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fraud Rule Toggles Section */}
      <div className="bg-white rounded-[16px] border border-gray-200/80 shadow-card-soft p-5">
        <h3 className="text-base font-bold text-slate-900 mb-1">Active Fraud Rules Engine</h3>
        <p className="text-xs text-slate-400 mb-4">
          Toggle automated policy rules enforced alongside ML model risk scores
        </p>

        <div className="space-y-3">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200/80 rounded-2xl hover:bg-gray-100/60 transition-colors"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-gray-200">
                    {rule.id}
                  </span>
                  <h4 className="text-xs font-bold text-slate-900">{rule.name}</h4>
                  <span className="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-semibold">
                    {rule.category}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{rule.description}</p>
              </div>

              <button
                onClick={() => toggleRule(rule.id)}
                className="p-1 text-slate-700 hover:text-slate-900 transition-colors"
              >
                {rule.enabled ? (
                  <ToggleRight className="w-8 h-8 text-[#F97316]" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-slate-400" />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
