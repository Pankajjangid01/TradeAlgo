import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState } from '../store/uiSlice';
import { api } from '../services/api';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Skeleton,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Remove as RemoveIcon,
  FlashOn as FlashOnIcon,
  Analytics as AnalyticsIcon,
  AccountBalance as AccountBalanceIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

const getStatusColor = (status: string) => {
  const colors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    approved: 'success',
    order_pending: 'warning',
    position_open: 'info',
    rejected: 'error',
    closed: 'default',
    wait_for_confirmation: 'warning',
  };
  return colors[status] || 'default';
};

const generateIntradayPnL = () => {
  const data = [];
  const start = new Date();
  start.setHours(9, 15, 0, 0);
  let pnl = 0;
  for (let i = 0; i < 390; i += 5) {
    const time = new Date(start.getTime() + i * 60000);
    pnl += (Math.random() - 0.48) * 200;
    data.push({
      time: time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      pnl: Math.round(pnl),
    });
  }
  return data;
};

const RiskMetricRow: React.FC<{ label: string; value: string; color: 'success' | 'warning' | 'error' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, color: color === 'success' ? 'success.main' : color === 'warning' ? 'warning.main' : 'error.main' }}>
      {value}
    </Typography>
  </Box>
);

const Dashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const isConnected = useSelector((state: RootState) => state.market.isConnected);
  const tradingMode = useSelector((state: RootState) => state.trading.tradingMode);
  const isTradingEnabled = useSelector((state: RootState) => state.trading.isTradingEnabled);
  const positions = useSelector((state: RootState) => state.trading.positions);
  const orders = useSelector((state: RootState) => state.trading.orders);
  const funds = useSelector((state: RootState) => state.trading.funds);
  const riskMetrics = useSelector((state: RootState) => state.trading.riskMetrics);
  const signals = useSelector((state: RootState) => state.signals.signals);
  const loading = useSelector((state: RootState) => state.ui.loadingStates.dashboard || false);

  const openPositions = positions.filter(p => p.isOpen);
  const totalUnrealizedPnl = openPositions.reduce((sum, p) => sum + p.unrealizedPnl, 0);
  const totalRealizedPnl = positions.reduce((sum, p) => sum + p.realizedPnl, 0);
  const pendingOrders = orders.filter(o => ['acknowledged', 'partially_filled', 'submitted'].includes(o.status)).length;

  useEffect(() => {
    dispatch(setLoadingState({ key: 'dashboard', loading: true }));
    const loadData = async () => {
      try {
        await Promise.all([
          api.getFunds(),
          api.getPositions(),
          api.getOrders(),
        ]);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        dispatch(setLoadingState({ key: 'dashboard', loading: false }));
      }
    };
    loadData();
  }, [dispatch]);

  const statCards = [
    {
      title: 'Total P&L',
      value: (totalUnrealizedPnl + totalRealizedPnl).toFixed(2),
      change: totalUnrealizedPnl.toFixed(2),
      icon: <TrendingUpIcon />,
      color: totalUnrealizedPnl + totalRealizedPnl >= 0 ? 'success' : 'error',
      subtitle: `Unrealized: ${totalUnrealizedPnl.toFixed(2)} | Realized: ${totalRealizedPnl.toFixed(2)}`,
    },
    {
      title: 'Available Margin',
      value: funds?.availableMargin.toLocaleString() || '0',
      change: funds?.usedMargin.toLocaleString() || '0',
      icon: <AccountBalanceIcon />,
      color: 'info',
      subtitle: `Used: ${funds?.usedMargin.toLocaleString() || '0'}`,
    },
    {
      title: 'Open Positions',
      value: openPositions.length.toString(),
      change: `${riskMetrics.openPositions}/${riskMetrics.maxPositions}`,
      icon: <AnalyticsIcon />,
      color: openPositions.length >= riskMetrics.maxPositions ? 'warning' : 'success',
      subtitle: riskMetrics.maxPositions > 0 ? `Max: ${riskMetrics.maxPositions}` : 'No limit',
    },
    {
      title: 'Pending Orders',
      value: pendingOrders.toString(),
      change: orders.length.toString(),
      icon: <NotificationsIcon />,
      color: pendingOrders > 0 ? 'warning' : 'success',
      subtitle: `Total: ${orders.length}`,
    },
    {
      title: 'Daily P&L',
      value: riskMetrics.dailyPnl.toFixed(2),
      change: `${((riskMetrics.dailyPnl / riskMetrics.dailyLossLimit) * 100).toFixed(1)}% of limit`,
      icon: <FlashOnIcon />,
      color: riskMetrics.dailyPnl < -riskMetrics.dailyLossLimit * 0.8 ? 'error' : (riskMetrics.dailyPnl < 0 ? 'warning' : 'success'),
      subtitle: `Limit: ${riskMetrics.dailyLossLimit.toLocaleString()}`,
    },
    {
      title: 'Signals Today',
      value: signals.filter(s => new Date(s.createdAt).toDateString() === new Date().toDateString()).length.toString(),
      change: signals.length.toString(),
      icon: <SecurityIcon />,
      color: 'info',
      subtitle: `Active: ${signals.filter(s => ['approved', 'order_pending', 'position_open'].includes(s.status)).length}`,
    },
  ];

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            TradeIQ Algo Trading Platform - {tradingMode.toUpperCase()} MODE
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Chip
            icon={<CircularProgress size={14} color="inherit" />}
            label={isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
            variant="outlined"
          />
          <Chip
            label={tradingMode.toUpperCase()}
            color={tradingMode === 'live' ? 'error' : 'success'}
            size="small"
            variant={tradingMode === 'live' ? 'filled' : 'outlined'}
          />
          <Chip
            label={isTradingEnabled ? 'ENABLED' : 'DISABLED'}
            color={isTradingEnabled ? 'success' : 'warning'}
            size="small"
            variant={isTradingEnabled ? 'filled' : 'outlined'}
          />
        </Box>
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Stats Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((stat, index) => (
          <Grid item xs={12} sm={6} lg={4} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 0.5 }}>
                      {stat.title}
                    </Typography>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: stat.color === 'success' ? 'success.main' : stat.color === 'error' ? 'error.main' : stat.color === 'warning' ? 'warning.main' : stat.color === 'info' ? 'info.main' : 'text.primary' }}>
                      {stat.value}
                    </Typography>
                    <Typography variant="caption" color={stat.color === 'success' ? 'success.main' : stat.color === 'error' ? 'error.main' : stat.color === 'warning' ? 'warning.main' : 'text.secondary'} sx={{ mt: 0.5 }}>
                      {stat.change}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                      {stat.subtitle}
                    </Typography>
                  </Box>
                  <Box sx={{ p: 1, borderRadius: 2, bgcolor: `${stat.color === 'success' ? 'success' : stat.color === 'error' ? 'error' : stat.color === 'warning' ? 'warning' : 'info'}.light` }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Charts and Tables */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* P&L Chart */}
        <Grid item xs={12} lg={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Portfolio P&L (Intraday)
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={generateIntradayPnL()}>
                    <defs>
                      <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00d4aa" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                    <XAxis dataKey="time" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                    <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} tickFormatter={val => `₹${val.toLocaleString()}`} />
                    <Tooltip />
                    <Area type="monotone" dataKey="pnl" stroke="#00d4aa" fillOpacity={1} fill="url(#colorPnL)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Risk Metrics */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Risk Metrics
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <RiskMetricRow 
                  label="Daily Loss Used" 
                  value={`${Math.abs(riskMetrics.dailyPnl / riskMetrics.dailyLossLimit * 100).toFixed(1)}%`} 
                  color={riskMetrics.dailyPnl < -riskMetrics.dailyLossLimit * 0.8 ? 'error' : riskMetrics.dailyPnl < 0 ? 'warning' : 'success'} 
                />
                <RiskMetricRow 
                  label="Position Utilization" 
                  value={`${(riskMetrics.openPositions / riskMetrics.maxPositions * 100).toFixed(0)}%`} 
                  color={riskMetrics.openPositions >= riskMetrics.maxPositions ? 'error' : 'success'} 
                />
                <RiskMetricRow 
                  label="Consecutive Losses" 
                  value={`${riskMetrics.consecutiveLosses}/${riskMetrics.maxConsecutiveLosses}`} 
                  color={riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses * 0.7 ? 'warning' : 'success'} 
                />
                <RiskMetricRow 
                  label="Exposure Utilization" 
                  value={`${(riskMetrics.totalExposure / riskMetrics.maxExposure * 100).toFixed(1)}%`} 
                  color={riskMetrics.totalExposure >= riskMetrics.maxExposure * 0.8 ? 'warning' : 'success'} 
                />
                <RiskMetricRow 
                  label="Kill Switch" 
                  value={riskMetrics.killSwitchActive ? 'ACTIVE' : 'INACTIVE'} 
                  color={riskMetrics.killSwitchActive ? 'error' : 'success'} 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Open Positions */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Open Positions</Typography>
                <Chip label={openPositions.length} color="primary" size="small" />
              </Box>
              {openPositions.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  No open positions
                </Box>
              ) : (
                <Box sx={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #30363d' }}>
                        {['Symbol', 'Side', 'Qty', 'Avg Price', 'Current', 'Unrealized P&L', 'Stop', 'Target'].map(h => (
                          <th key={h} style={{ padding: '12px', textAlign: 'left', color: '#8b949e', fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {openPositions.map((pos, i) => (
                        <tr key={pos.id} style={{ borderBottom: i === openPositions.length - 1 ? 'none' : '1px solid #30363d' }}>
                          <td style={{ padding: '12px', fontWeight: 500 }}>{pos.symbol}</td>
                          <td style={{ padding: '12px' }}>
                            <Chip label={pos.side.toUpperCase()} size="small" color={pos.side === 'long' ? 'success' : 'error'} variant="outlined" />
                          </td>
                          <td style={{ padding: '12px' }}>{pos.quantity}</td>
                          <td style={{ padding: '12px' }}>₹{pos.averagePrice.toFixed(2)}</td>
                          <td style={{ padding: '12px' }}>₹{pos.currentPrice.toFixed(2)}</td>
                          <td style={{ padding: '12px', color: pos.unrealizedPnl >= 0 ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                            ₹{pos.unrealizedPnl.toFixed(2)}
                          </td>
                          <td style={{ padding: '12px' }}>{pos.stopPrice ? `₹${pos.stopPrice.toFixed(2)}` : '-'}</td>
                          <td style={{ padding: '12px' }}>{pos.targetPrice ? `₹${pos.targetPrice.toFixed(2)}` : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Signals */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Recent Signals</Typography>
                <Chip label={signals.length} color="info" size="small" />
              </Box>
              {signals.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  No signals generated
                </Box>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {signals.slice(0, 10).map((signal) => (
                    <Box key={signal.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{signal.instrument}</Typography>
                        <Chip
                          label={signal.direction.toUpperCase()}
                          size="small"
                          color={signal.direction === 'bullish' ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'text.secondary' }}>
                        <span>{signal.strategy}</span>
                        <span>RR: {signal.rrRatio.toFixed(1)}</span>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, fontSize: '0.75rem' }}>
                        <Chip label={signal.status.replace('_', ' ').toUpperCase()} size="small" variant="outlined" color={getStatusColor(signal.status)} />
                        <span>{new Date(signal.createdAt).toLocaleTimeString()}</span>
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;