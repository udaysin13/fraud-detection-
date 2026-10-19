/**
 * VaultGuard - Centralized API Client
 * Wraps all backend endpoints with structured error handling, timeouts, and configuration.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      let errorDetails = null;
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;

      try {
        errorDetails = await response.json();
        if (errorDetails.detail) {
          errorMessage = typeof errorDetails.detail === 'string'
            ? errorDetails.detail
            : JSON.stringify(errorDetails.detail);
        }
      } catch {
        // Not a JSON response
      }

      throw new ApiError(errorMessage, response.status, errorDetails);
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network errors, connection refused, CORS errors
    throw new ApiError(
      `Unable to connect to VaultGuard Backend at ${BASE_URL}. Please ensure the API is running.`,
      0,
      { originalError: err.message }
    );
  }
}

// ─── API Methods ─────────────────────────────────────────────────────────

export const apiClient = {
  // Health
  getHealth: () => request('/api/health'),

  // Analytics
  getAnalyticsOverview: () => request('/api/analytics/overview'),
  getRiskScoreSummary: () => request('/api/risk-score'),
  getTrend: (range = '24h') => request(`/api/trend?range=${encodeURIComponent(range)}`),

  // Transactions
  getTransactions: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.decision && params.decision !== 'All') query.set('decision', params.decision);
    if (params.risk_category && params.risk_category !== 'All') query.set('risk_category', params.risk_category);
    if (params.channel && params.channel !== 'All') query.set('channel', params.channel);
    if (params.segment && params.segment !== 'All') query.set('segment', params.segment);
    if (params.search) query.set('search', params.search);
    if (params.min_amount !== undefined && params.min_amount !== '') query.set('min_amount', params.min_amount);
    if (params.max_amount !== undefined && params.max_amount !== '') query.set('max_amount', params.max_amount);

    const qs = query.toString();
    return request(`/api/transactions${qs ? `?${qs}` : ''}`);
  },

  getTransactionById: (txnId) =>
    request(`/api/transactions/${encodeURIComponent(txnId)}`),

  // Live Real-Time Scoring
  predictTransaction: (payload) =>
    request('/api/predict', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Alerts
  getAlerts: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.status && params.status !== 'All') query.set('status', params.status);
    if (params.segment && params.segment !== 'All') query.set('segment', params.segment);
    if (params.search) query.set('search', params.search);

    const qs = query.toString();
    return request(`/api/alerts${qs ? `?${qs}` : ''}`);
  },

  createAlert: (payload) =>
    request('/api/alerts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateAlert: (alertId, payload) =>
    request(`/api/alerts/${alertId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  // Entities
  getCustomers: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.risk_level && params.risk_level !== 'All') query.set('risk_level', params.risk_level);
    if (params.search) query.set('search', params.search);

    const qs = query.toString();
    return request(`/api/customers${qs ? `?${qs}` : ''}`);
  },

  getMerchants: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.category && params.category !== 'All') query.set('category', params.category);
    if (params.risk_level && params.risk_level !== 'All') query.set('risk_level', params.risk_level);
    if (params.search) query.set('search', params.search);

    const qs = query.toString();
    return request(`/api/merchants${qs ? `?${qs}` : ''}`);
  },

  getCases: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page);
    if (params.limit) query.set('limit', params.limit);
    if (params.status && params.status !== 'All') query.set('status', params.status);
    if (params.search) query.set('search', params.search);

    const qs = query.toString();
    return request(`/api/cases${qs ? `?${qs}` : ''}`);
  },

  getActiveCaseQueue: (params = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.set('limit', params.limit);
    if (params.search) query.set('search', params.search);
    const qs = query.toString();
    return request(`/api/cases/active${qs ? `?${qs}` : ''}`);
  },

  updateCaseStatus: (caseId, status) =>
    request(`/api/cases/${encodeURIComponent(caseId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  updateFraudAlertStatus: (alertId, status) =>
    request(`/api/fraud-alerts/${alertId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  // Model Metrics & Retraining
  getModelMetrics: () => request('/api/models/metrics'),

  retrainModel: () =>
    request('/api/models/retrain', {
      method: 'POST',
    }),

  // Export URL helper
  getExportUrl: () => `${BASE_URL}/api/export?type=csv`,
};
