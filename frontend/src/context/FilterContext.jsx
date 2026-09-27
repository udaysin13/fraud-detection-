import React, { createContext, useContext, useState, useEffect } from 'react';

const FilterContext = createContext(null);

export const FilterProvider = ({ children }) => {
  const [region, setRegion] = useState('EU Payments');
  const [timeRange, setTimeRange] = useState('24h');
  const [currency, setCurrency] = useState('USD');
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateAlertOpen, setIsCreateAlertOpen] = useState(false);

  // Live WebSocket streaming state
  const [liveTransactions, setLiveTransactions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connectWS = () => {
      ws = new WebSocket('ws://localhost:8000/ws/transactions');

      ws.onopen = () => {
        setWsConnected(true);
        console.log('[WebSocket] Connected to live VaultGuard transaction stream.');
      };

      ws.onmessage = (event) => {
        try {
          const newTxn = JSON.parse(event.data);

          // Format reasons if stringified JSON
          let parsedReasons = newTxn.reasons;
          if (typeof parsedReasons === 'string') {
            try {
              parsedReasons = JSON.parse(parsedReasons);
            } catch {
              parsedReasons = [parsedReasons];
            }
          }
          newTxn.reasons = parsedReasons;

          // Append to live feed (keep last 25)
          setLiveTransactions((prev) => [newTxn, ...prev.slice(0, 24)]);

          // If high risk or block, push notification
          if (newTxn.decision === 'Block' || newTxn.risk_score > 70.0) {
            const notif = {
              id: Date.now(),
              title: `High-Risk Transaction Flagged (${newTxn.decision})`,
              txnId: newTxn.transaction_id,
              amount: newTxn.amount,
              riskScore: newTxn.risk_score,
              reasons: newTxn.reasons,
              timestamp: newTxn.timestamp,
            };
            setNotifications((prev) => [notif, ...prev.slice(0, 9)]);
            setUnreadCount((count) => count + 1);
          }
        } catch (err) {
          console.error('[WebSocket Error] Error parsing frame:', err);
        }
      };

      ws.onerror = () => {
        setWsConnected(false);
      };

      ws.onclose = () => {
        setWsConnected(false);
        // Attempt reconnect after 5s
        reconnectTimer = setTimeout(connectWS, 5000);
      };
    };

    connectWS();

    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const clearNotifications = () => {
    setUnreadCount(0);
  };

  return (
    <FilterContext.Provider
      value={{
        region,
        setRegion,
        timeRange,
        setTimeRange,
        currency,
        setCurrency,
        searchQuery,
        setSearchQuery,
        isCreateAlertOpen,
        setIsCreateAlertOpen,
        liveTransactions,
        notifications,
        unreadCount,
        clearNotifications,
        wsConnected,
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
