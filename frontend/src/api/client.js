
/**
 * VaultGuard - Centralized API Client
 * Wraps all backend endpoints with structured error handling,
 * timeouts, and configuration.
 */

// Production backend URL for Vercel deployment.
// You can override it using VITE_API_BASE_URL.
export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "https://fraud-detection-topaz.vercel.app";

export const API_BASE_URL = BASE_URL;

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;

  const config = {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
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
          errorMessage =
            typeof errorDetails.detail === "string"
              ? errorDetails.detail
              : JSON.stringify(errorDetails.detail);
        }
      } catch {
        // Response was not JSON.
      }

      throw new ApiError(
        errorMessage,
        response.status,
        errorDetails
      );
    }

    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }

    throw new ApiError(
      `Unable to connect to VaultGuard Backend at ${BASE_URL}. Check the backend URL, CORS settings, and network connection.`,
      0,
      { originalError: err.message }
    );
  }
}

// ─── API Methods ───────────────────────────────────────────────

export const apiClient = {
  // Health
  getHealth: () => request("/api/health"),

  // Analytics
  getAnalyticsOverview: () =>
    request("/api/analytics/overview"),

  getRiskScoreSummary: () =>
    request("/api/risk-score"),

  getTrend: (range = "24h") =>
    request(`/api/trend?range=${encodeURIComponent(range)}`),

  // Transactions
  getTransactions: (params = {}) => {
    const query = new URLSearchParams();

    if (params.page) query.set("page", params.page);
    if (params.limit) query.set("limit", params.limit);

    if (params.decision && params.decision !== "All")
      query.set("decision", params.decision);

    if (params.risk_category && params.risk_category !== "All")
      query.set("risk_category", params.risk_category);

    if (params.channel && params.channel !== "All")
      query.set("channel", params.channel);

    if (params.segment && params.segment !== "All")
      query.set("segment", params.segment);

    if (params.search)
      query.set("search", params.search);

    if (params.min_amount !== undefined && params.min_amount !== "")
      query.set("min_amount", params.min_amount);

    if (params.max_amount !== undefined && params.max_amount !== "")
      query.set("max_amount", params.max_amount);

    const qs = query.toString();

    return request(`/api/transactions${qs ? `?${qs}` : ""}`);
  },

  getTransactionById: (txnId) =>
    request(`/api/transactions/${encodeURIComponent(txnId)}`),

  // Live Real-Time Scoring
  predictTransaction: (payload) =>
    request("/api/predict", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Alerts
  getAlerts: (params = {}) => {
    const query = new URLSearchParams();

    if (params.page) query.set("page", params.page);
    if (params.limit) query.set("limit", params.limit);

    if (params.status && params.status !== "All")
      query.set("status", params.status);

    if (params.segment && params.segment !== "All")
      query.set("segment", params.segment);

    if (params.severity && params.severity !== "All")
      query.set("severity", params.severity);

    if (params.search)
      query.set("search", params.search);

    const qs = query.toString();

    return request(`/api/alerts${qs ? `?${qs}` : ""}`);
  },

  createAlert: (payload) =>
    request("/api/alerts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateAlert: (alertId, payload) =>
    request(`/api/alerts/${encodeURIComponent(alertId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Customers
  getCustomers: (params = {}) => {
    const query = new URLSearchParams();

    if (params.page) query.set("page", params.page);
    if (params.limit) query.set("limit", params.limit);

    if (params.risk_level && params.risk_level !== "All")
      query.set("risk_level", params.risk_level);

    if (params.search)
      query.set("search", params.search);

    const qs = query.toString();

    return request(`/api/customers${qs ? `?${qs}` : ""}`);
  },

  // Merchants
  getMerchants: (params = {}) => {
    const query = new URLSearchParams();

    if (params.page) query.set("page", params.page);
    if (params.limit) query.set("limit", params.limit);

    if (params.category && params.category !== "All")
      query.set("category", params.category);

    if (params.risk_level && params.risk_level !== "All")
      query.set("risk_level", params.risk_level);

    if (params.search)
      query.set("search", params.search);

    const qs = query.toString();

    return request(`/api/merchants${qs ? `?${qs}` : ""}`);
  },

  // Cases
  getCases: (params = {}) => {
    const query = new URLSearchParams();

    if (params.page) query.set("page", params.page);
    if (params.limit) query.set("limit", params.limit);

    if (params.status && params.status !== "All")
      query.set("status", params.status);

    if (params.search)
      query.set("search", params.search);

    const qs = query.toString();

    return request(`/api/cases${qs ? `?${qs}` : ""}`);
  },

  getActiveCaseQueue: (params = {}) => {
    const query = new URLSearchParams();

    if (params.limit) query.set("limit", params.limit);
    if (params.search) query.set("search", params.search);

    const qs = query.toString();

    return request(`/api/cases/active${qs ? `?${qs}` : ""}`);
  },

  updateCaseStatus: (caseId, status) =>
    request(
      `/api/cases/${encodeURIComponent(caseId)}/status`,
      {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }
    ),

  createCase: (payload) =>
    request("/api/cases", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCaseNotes: (caseId) =>
    request(`/api/cases/${encodeURIComponent(caseId)}/notes`),

  addCaseNote: (caseId, payload) =>
    request(`/api/cases/${encodeURIComponent(caseId)}/notes`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCaseHistory: (caseId) =>
    request(`/api/cases/${encodeURIComponent(caseId)}/history`),

  updateFraudAlertStatus: (alertId, status) =>
    request(
      `/api/fraud-alerts/${encodeURIComponent(alertId)}/status`,
      {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }
    ),

  // Model Metrics & Retraining
  getModelMetrics: () =>
    request("/api/models/metrics"),

  retrainModel: () =>
    request("/api/models/retrain", {
      method: "POST",
    }),

  // Bulk CSV Analysis
  uploadBulkCsv: async (file) => {
    const form = new FormData();
    form.append("file", file);

    try {
      const response = await fetch(
        `${BASE_URL}/api/bulk-analysis/upload`,
        {
          method: "POST",
          body: form,
        }
      );

      if (!response.ok) {
        let body = {};

        try {
          body = await response.json();
        } catch {
          // Response was not JSON.
        }

        throw new ApiError(
          body.detail || `Upload failed (${response.status})`,
          response.status,
          body
        );
      }

      return await response.json();
    } catch (err) {
      if (err instanceof ApiError) throw err;

      throw new ApiError(
        `Unable to upload CSV to ${BASE_URL}. Check backend connectivity and CORS settings.`,
        0,
        { originalError: err.message }
      );
    }
  },

  getBulkSchema: () =>
    request("/api/bulk-analysis/schema"),

  getBulkSampleUrl: () =>
    `${BASE_URL}/api/bulk-analysis/sample.csv`,

  getBulkExportUrl: (analysisId) =>
    `${BASE_URL}/api/bulk-analysis/${encodeURIComponent(analysisId)}/export`,

  // Rules
  getRules: () =>
    request("/api/rules"),

  // Export
  getExportUrl: () =>
    `${BASE_URL}/api/export?type=csv`,

  downloadExportCSV: async () => {
    try {
      const response = await fetch(BASE_URL + "/api/export?type=csv", {
        headers: { Accept: "text/csv, application/csv, */*" },
      });

      if (!response.ok) {
        let detail = "CSV export failed (HTTP " + response.status + ").";
        try {
          const body = await response.json();
          if (body?.detail) {
            detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          // Keep the HTTP error when the server does not return JSON.
        }
        throw new ApiError(detail, response.status);
      }

      const blob = await response.blob();
      if (!blob.size) {
        throw new ApiError("The server returned an empty CSV export.", response.status);
      }
      return blob;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(
        "Unable to download CSV from " + BASE_URL + ". Check backend connectivity and CORS settings.",
        0,
        { originalError: err.message }
      );
    }
  },
};
