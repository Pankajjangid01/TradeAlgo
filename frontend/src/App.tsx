import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from './store/index';
import { setConnectionStatus } from './store/marketSlice';
import { wsService } from './services/websocket';
import { api } from './services/api';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import MarketAnalysis from './pages/MarketAnalysis';
import SignalCenter from './pages/SignalCenter';
import TradingTerminal from './pages/TradingTerminal';
import Backtesting from './pages/Backtesting';
import MLMonitoring from './pages/MLMonitoring';
import RiskConsole from './pages/RiskConsole';
import AuditLogs from './pages/AuditLogs';
import Settings from './pages/Settings';
import Login from './pages/Login';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useSelector((state: RootState) => !!localStorage.getItem('auth_token'));
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const App: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    // Initialize WebSocket
    wsService.connect();

    // Setup connection listener
    const unsubscribeConnection = wsService.onConnectionChange((connected) => {
      dispatch(setConnectionStatus({ connected, error: connected ? undefined : 'Disconnected from server' }));
    });

    // Setup market data listeners
    const unsubscribeTicks = wsService.onMarketData('tick', (data) => {
      // Handle tick data - would dispatch to market slice
      console.log('Tick received:', data);
    });

    const unsubscribeCandles = wsService.onMarketData('candle', (data) => {
      console.log('Candle received:', data);
    });

    const unsubscribeSignals = wsService.onMarketData('signal', (data) => {
      console.log('Signal received:', data);
    });

    const unsubscribeOrderUpdates = wsService.onMarketData('order_update', (data) => {
      console.log('Order update:', data);
    });

    const unsubscribePositionUpdates = wsService.onMarketData('position_update', (data) => {
      console.log('Position update:', data);
    });

    const unsubscribeRiskAlerts = wsService.onMarketData('risk_alert', (data) => {
      console.log('Risk alert:', data);
    });

    // Check auth on mount
    const token = localStorage.getItem('auth_token');
    api.setAuthToken(token);

    return () => {
      unsubscribeConnection();
      unsubscribeTicks();
      unsubscribeCandles();
      unsubscribeSignals();
      unsubscribeOrderUpdates();
      unsubscribePositionUpdates();
      unsubscribeRiskAlerts();
      wsService.disconnect();
    };
  }, [dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="market-analysis" element={<MarketAnalysis />} />
          <Route path="signals" element={<SignalCenter />} />
          <Route path="trading" element={<TradingTerminal />} />
          <Route path="backtesting" element={<Backtesting />} />
          <Route path="ml-monitoring" element={<MLMonitoring />} />
          <Route path="risk" element={<RiskConsole />} />
          <Route path="audit" element={<AuditLogs />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
