import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '../api/client';

const FilterContext = createContext(null);

const WS_URL = import.meta.env.VITE_WS_URL || 'wss://YOUR-NEW-BACKEND-URL.vercel.app';
const MAX_LIVE_EVENTS = 30;
const MAX_NOTIFICATIONS = 15;

export const FilterProvider = ({ children }) => {
  // Global filter states for Indian digital payments
  const [selectedChannel, setSelectedChannel] = useState('All');
  const [timeRange, setTimeRange] = useState('24h');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals & Drawers
  const [isCreateAlertOpen, setIsCreateAlertOpen] = useState(false);
  const [isAboutModalOpen, setIsAboutModalOpen] = useState(false);
  const [selectedTransactionId, setSelectedTransactionId] = useState(null);

  // Backend Health state
  const [backendHealth, setBackendHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);

  // Live WebSocket state
  const [liveTransactions, setLiveTransactions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [wsStatus, setWsStatus] = useState('disconnected'); // 'connected' | 'reconnecting' | 'disconnected'
  const [wsError, setWsError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const seenTxnIdsRef = useRef(new Set());

  // Fetch backend health
  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await apiClient.getHealth();
      setBackendHealth(data);
      return data;
    } catch (err) {
      setHealthError(err.message || 'Backend unreachable');
      setBackendHealth(null);
      return null;
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    // Poll health check every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // WebSocket Connection Management
  const connectWebSocket = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      setWsStatus(reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'disconnected');
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        setWsError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const rawItem = JSON.parse(event.data);

          // Duplicate event prevention
          const txnId = rawItem.transaction_id || `TXN_${Date.now()}`;
          if (seenTxnIdsRef.current.has(txnId)) {
            return;
          }
          seenTxnIdsRef.current.add(txnId);
          if (seenTxnIdsRef.current.size > 200) {
            // Keep memory bound
            const [firstKey] = seenTxnIdsRef.current;
            seenTxnIdsRef.current.delete(firstKey);
          }

          // Parse reasons
          let parsedReasons = rawItem.reasons;
          if (typeof parsedReasons === 'string') {
            try {
              parsedReasons = JSON.parse(parsedReasons);
            } catch {
              parsedReasons = [parsedReasons];
            }
          }
          if (!Array.isArray(parsedReasons)) {
            parsedReasons = [String(parsedReasons || 'Suspicious velocity signature')];
          }

          const streamItem = {
            ...rawItem,
            reasons: parsedReasons,
            isSimulated: true, // Explicit flag indicating simulated stream event
            receivedAt: new Date().toISOString(),
          };

          // Append to bounded in-memory live stream
          setLiveTransactions((prev) => [streamItem, ...prev.slice(0, MAX_LIVE_EVENTS - 1)]);

          // Push to alerts notification badge if high-risk or manual review
          if (streamItem.decision === 'Block' || streamItem.risk_score > 60.0) {
            const notif = {
              id: `${txnId}_${Date.now()}`,
              transaction_id: txnId,
              title: streamItem.decision === 'Block' ? 'High-risk review recommended' : 'Suspicious anomaly flagged',
              channel: streamItem.channel || 'UPI_P2P',
              amount_inr: streamItem.amount_inr ?? streamItem.amount,
              risk_score: streamItem.risk_score,
              decision: streamItem.decision,
              topReason: parsedReasons[0] || 'Unusual payment activity',
              timestamp: streamItem.timestamp || new Date().toLocaleTimeString(),
              isSimulated: true,
            };

            setNotifications((prev) => [notif, ...prev.slice(0, MAX_NOTIFICATIONS - 1)]);
            setUnreadCount((c) => c + 1);
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message frame:', err);
        }
      };

      ws.onerror = (err) => {
        setWsError('WebSocket connection error');
        setWsStatus('disconnected');
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        // Exponential backoff reconnect: 3s, 6s, 12s... max 20s
        const backoff = Math.min(3000 * Math.pow(1.5, reconnectAttemptsRef.current), 20000);
        reconnectAttemptsRef.current += 1;

        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, backoff);
      };
    } catch (err) {
      setWsStatus('disconnected');
      setWsError(err.message);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const clearNotifications = useCallback(() => {
    setUnreadCount(0);
  }, []);

  const manualReconnectWS = useCallback(() => {
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    reconnectAttemptsRef.current = 0;
    connectWebSocket();
  }, [connectWebSocket]);

  return (
    <FilterContext.Provider
      value={{
        selectedChannel,
        setSelectedChannel,
        timeRange,
        setTimeRange,
        searchQuery,
        setSearchQuery,
        // Modals
        isCreateAlertOpen,
        setIsCreateAlertOpen,
        isAboutModalOpen,
        setIsAboutModalOpen,
        selectedTransactionId,
        setSelectedTransactionId,
        // Backend health
        backendHealth,
        healthLoading,
        healthError,
        checkHealth,
        // Live stream
        liveTransactions,
        notifications,
        unreadCount,
        clearNotifications,
        wsStatus,
        wsError,
        manualReconnectWS,
      }}
    >
      {children}
    </FilterContext.Provider>
  );
};

export const useFilter = () => {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useFilter must be used within a FilterProvider');
  }
  return context;
};
