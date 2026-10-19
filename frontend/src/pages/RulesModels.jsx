import React, { useState, useEffect, useCallback } from 'react';
import {
  Sliders,
  RefreshCw,
  Cpu,
  CheckCircle2,
  ShieldCheck,
  Zap,
  TrendingUp,
  Activity,
  Layers,
  AlertTriangle,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BackendErrorBanner } from '../components/BackendErrorBanner';
import { formatIndianNumber } from '../utils/formatters';

export const RulesModels = () => {
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [error, setError] = useState(null);
  const [retraining, setRetraining] = useState(false);
  const [retrainSuccess, setRetrainSuccess] = useState(false);

  const modeledSignals = [
    {
      name: 'Device and SIM-change signals',
      description: 'New-device and recent SIM-change features are included in the prediction input.',
      category: 'Account Takeover (ATO)',
    },
    {
      name: 'Prior transaction velocity',
      description: 'Past-only transaction counts are computed for short and long time windows.',
      category: 'Transaction history',
    },
    {
      name: 'Amount pattern features',
      description: 'The pipeline derives small-amount and near-threshold features from the transaction amount.',
      category: 'Amount',
    },
    {
      name: 'Merchant activity history',
      description: 'Merchant volume is compared with a past-history baseline when available.',
      category: 'Merchant activity',
    },
    {
      name: 'Transaction type',
      description: 'Payment type, including collect requests, is encoded as a model feature.',
      category: 'Payment context',
    },
  ];

  const fetchMetrics = useCallback(async () => {
    setLoadingMetrics(true);
    setError(null);
    try {
      const data = await apiClient.getModelMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch model metrics:', err);
      setError(err.message || 'Unable to retrieve ML model metrics.');
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainSuccess(false);
    setError(null);
    try {
      const updated = await apiClient.retrainModel();
      setMetrics(updated);
      setRetrainSuccess(true);
      setTimeout(() => setRetrainSuccess(false), 5000);
    } catch (err) {
      console.error('Retraining failed:', err);
      setError(err.message || 'Model retraining pipeline encountered an issue.');
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-50 border border-teal-200 text-teal-600 rounded-xl">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Model Insights</h2>
            <p className="text-xs text-slate-400">
              Saved model evaluation metrics and feature-pipeline details
            </p>
          </div>
        </div>

        <button
          onClick={handleRetrain}
          disabled={retraining}
          className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-slate-800 rounded-lg text-xs font-bold transition-all shadow-md flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${retraining ? 'animate-spin' : ''}`} />
          <span>{retraining ? 'Re-training Pipeline...' : 'Re-train ML Pipeline'}</span>
        </button>
      </div>

      {retrainSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Pipeline re-training completed! Serialized models and metrics updated successfully.</span>
        </div>
      )}

      {error && (
        <BackendErrorBanner
          error={error}
          onRetry={fetchMetrics}
          isRetrying={loadingMetrics}
        />
      )}

      {/* Benchmark Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <span className="text-xs text-slate-400 block mb-1">Precision (Test Split)</span>
          <div className="text-2xl font-extrabold text-teal-600">
            {metrics ? `${(metrics.precision * 100).toFixed(1)}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Synthetic test split</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <span className="text-xs text-slate-400 block mb-1">Recall (Fraud Catch Rate)</span>
          <div className="text-2xl font-extrabold text-emerald-600">
            {metrics ? `${(metrics.recall * 100).toFixed(1)}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Synthetic test split</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <span className="text-xs text-slate-400 block mb-1">F1 Score</span>
          <div className="text-2xl font-extrabold text-blue-500">
            {metrics ? `${(metrics.f1_score * 100).toFixed(1)}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Synthetic test split</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card-soft">
          <span className="text-xs text-slate-400 block mb-1">ROC-AUC / PR-AUC</span>
          <div className="text-2xl font-extrabold text-blue-700">
            {metrics ? `${(metrics.roc_auc * 100).toFixed(1)}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">PR-AUC: {metrics?.pr_auc != null ? `${(metrics.pr_auc * 100).toFixed(1)}%` : '—'}</span>
        </div>
      </div>

      {/* Model Benchmark Details & Confusion Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Confusion Matrix (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
          <div className="pb-3 border-b border-slate-200">
            <h3 className="text-sm font-bold text-slate-800">Out-of-Time Test Confusion Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {metrics?.test_sample_count ? `Synthetic chronological test split (${formatIndianNumber(metrics.test_sample_count)} records)` : 'Synthetic chronological test split'}
            </p>
          </div>

          {metrics?.confusion_matrix ? (
            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">True Negatives</span>
                  <span className="text-lg font-bold text-emerald-600">
                    {formatIndianNumber(metrics.confusion_matrix[0][0])}
                  </span>
                    <p className="text-[10px] text-slate-500 mt-0.5">Correctly classified non-fraud</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">False Positives</span>
                  <span className="text-lg font-bold text-rose-500">
                    {formatIndianNumber(metrics.confusion_matrix[0][1])}
                  </span>
                  <p className="text-[10px] text-slate-500 mt-0.5">False Alarms</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">False Negatives</span>
                  <span className="text-lg font-bold text-amber-600">
                    {formatIndianNumber(metrics.confusion_matrix[1][0])}
                  </span>
                  <p className="text-[10px] text-slate-500 mt-0.5">Missed Frauds</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase block mb-1">True Positives</span>
                  <span className="text-lg font-bold text-teal-600">
                    {formatIndianNumber(metrics.confusion_matrix[1][1])}
                  </span>
                    <p className="text-[10px] text-slate-500 mt-0.5">Correctly classified fraud</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-500">{loadingMetrics ? 'Loading matrix...' : 'Confusion matrix unavailable.'}</div>
          )}

          <div className="text-[11px] text-slate-400 bg-slate-50 p-3 rounded-lg border border-slate-200">
            Validation threshold: <strong className="text-teal-600">{metrics?.selected_threshold ?? 'Unavailable'}</strong>. Metrics are from synthetic data and do not establish real-world banking accuracy.
          </div>
        </div>

        {/* Model feature signals */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5 shadow-card-soft space-y-4">
          <div className="pb-3 border-b border-slate-200">
            <h3 className="text-sm font-bold text-slate-800">Modeled transaction signals</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Feature inputs used by the saved pipeline. These are not independently configurable rules.
            </p>
          </div>

          <div className="space-y-3">
            {modeledSignals.map((signal) => (
              <div
                key={signal.name}
                className="bg-slate-50 border border-slate-200 rounded-md p-3.5 text-xs"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 text-[9px] uppercase font-bold">
                      {signal.category}
                    </span>
                  </div>
                  <h4 className="font-bold text-slate-800 text-xs">{signal.name}</h4>
                  <p className="text-[11px] text-slate-500">{signal.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
