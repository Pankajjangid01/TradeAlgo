import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification } from '../store/uiSlice';
import { api } from '../services/api';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Slider,
  Switch,
  Tooltip,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  AccountBalance as AccountBalanceIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

const TradingTerminal: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const positions = useSelector((state: RootState) => state.trading.positions);
  const orders = useSelector((state: RootState) => state.trading.orders);
  const funds = useSelector((state: RootState) => state.trading.funds);
  const riskMetrics = useSelector((state: RootState) => state.trading.riskMetrics);
  const tradingMode = useSelector((state: RootState) => state.trading.tradingMode);
  const isTradingEnabled = useSelector((state: RootState) => state.trading.isTradingEnabled);
  const selectedBroker = useSelector((state: RootState) => state.trading.selectedBroker);

  const openPositions = positions.filter(p => p.isOpen);
  const pendingOrders = orders.filter(o => ['acknowledged', 'partially_filled', 'submitted'].includes(o.status));
  const [activeTab, setActiveTab] = useState(0);
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [orderForm, setOrderForm] = useState({
    symbol: 'NIFTY',
    side: 'buy',
    orderType: 'market',
    quantity: 75,
    price: '',
    triggerPrice: '',
    productType: 'MIS',
  });

  const handleOrderSubmit = async () => {
    try {
      await api.placeOrder({
        ...orderForm,
        quantity: parseInt(orderForm.quantity.toString()),
        price: orderForm.price ? parseFloat(orderForm.price) : undefined,
        triggerPrice: orderForm.triggerPrice ? parseFloat(orderForm.triggerPrice) : undefined,
      });
      addNotification({ type: 'success', message: 'Order placed successfully' });
      setOrderDialogOpen(false);
    } catch (error: any) {
      addNotification({ type: 'error', message: error.response?.data?.detail || 'Failed to place order' });
    }
  };

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Trading Terminal</Typography>
          <Typography variant="body2" color="text.secondary">Order management and position monitoring</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Badge badgeContent={tradingMode === 'live' ? 'LIVE' : 'PAPER'} color={tradingMode === 'live' ? 'error' : 'success'} variant="dot">
            <Chip label={tradingMode.toUpperCase()} size="small" variant="outlined" />
          </Badge>
          <Chip label={selectedBroker.toUpperCase()} size="small" variant="outlined" color="info" />
          <Switch
            checked={isTradingEnabled}
            onChange={(e) => dispatch({ type: 'trading/setTradingEnabled', payload: e.target.checked })}
            size="small"
            color="success"
          />
          <Tooltip title={isTradingEnabled ? 'Trading Enabled' : 'Trading Disabled'}>
            <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'uppercase' }}>
              {isTradingEnabled ? 'ENABLED' : 'DISABLED'}
            </Typography>
          </Tooltip>
        </Box>
      </Box>

      {/* Risk Bar */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              <RiskStat label="Daily P&L" value={`₹${riskMetrics.dailyPnl.toLocaleString()}`} color={riskMetrics.dailyPnl >= 0 ? 'success' : 'error'} />
              <RiskStat label="Daily Limit" value={`₹${riskMetrics.dailyLossLimit.toLocaleString()}`} color="info" />
              <RiskStat label="Positions" value={`${openPositions.length}/${riskMetrics.maxPositions}`} color={openPositions.length >= riskMetrics.maxPositions ? 'warning' : 'success'} />
              <RiskStat label="Exposure" value={`₹${riskMetrics.totalExposure.toLocaleString()}`} color="info" />
              <RiskStat label="Max Exposure" value={`₹${riskMetrics.maxExposure.toLocaleString()}`} color="info" />
              <RiskStat label="Consecutive Losses" value={`${riskMetrics.consecutiveLosses}/${riskMetrics.maxConsecutiveLosses}`} color={riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses ? 'error' : 'success'} />
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant={riskMetrics.killSwitchActive ? 'contained' : 'outlined'}
                color="error"
                onClick={() => dispatch({ type: 'trading/toggleKillSwitch' })}
                startIcon={riskMetrics.killSwitchActive ? <CheckCircleIcon /> : <WarningIcon />}
              >
                {riskMetrics.killSwitchActive ? 'KILL SWITCH ACTIVE' : 'ACTIVATE KILL SWITCH'}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3 }}>
        <Tab label="Positions" icon={<AccountBalanceIcon />} />
        <Tab label="Orders" icon={<TrendingUpIcon />} />
        <Tab label="New Order" icon={<AddIcon />} />
      </Tabs>

      {activeTab === 0 && (
        <Grid container spacing={3}>
          {/* Open Positions */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>Open Positions ({openPositions.length})</Typography>
                  <Chip label={openPositions.length} color="primary" size="small" />
                </Box>
                {openPositions.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>No open positions</Box>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Side</TableCell>
                          <TableCell>Qty</TableCell>
                          <TableCell>Avg Price</TableCell>
                          <TableCell>Current</TableCell>
                          <TableCell>Unrealized P&L</TableCell>
                          <TableCell>Stop Loss</TableCell>
                          <TableCell>Target</TableCell>
                          <TableCell>Actions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {openPositions.map((pos) => (
                          <TableRow key={pos.id}>
                            <TableCell sx={{ fontWeight: 600 }}>{pos.symbol}</TableCell>
                            <TableCell>
                              <Chip label={pos.side.toUpperCase()} size="small" color={pos.side === 'long' ? 'success' : 'error'} variant="outlined" />
                            </TableCell>
                            <TableCell>{pos.quantity}</TableCell>
                            <TableCell>₹{pos.averagePrice.toFixed(2)}</TableCell>
                            <TableCell>₹{pos.currentPrice.toFixed(2)}</TableCell>
                            <TableCell sx={{ fontWeight: 600, color: pos.unrealizedPnl >= 0 ? 'success.main' : 'error.main' }}>
                              ₹{pos.unrealizedPnl.toFixed(2)}
                            </TableCell>
                            <TableCell>{pos.stopPrice ? `₹${pos.stopPrice.toFixed(2)}` : '-'}</TableCell>
                            <TableCell>{pos.targetPrice ? `₹${pos.targetPrice.toFixed(2)}` : '-'}</TableCell>
                            <TableCell>
                              <Button size="small" color="error" variant="outlined" onClick={() => {}}>Exit</Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Funds & Margin */}
          <Grid item xs={12} lg={4}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Funds & Margin</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <FundRow label="Available Cash" value={funds?.availableCash || 0} />
                  <FundRow label="Available Margin" value={funds?.availableMargin || 0} color="primary" />
                  <FundRow label="Used Margin" value={funds?.usedMargin || 0} color="warning" />
                  <FundRow label="Total Collateral" value={funds?.totalCollateral || 0} color="info" />
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Quick Actions</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Button variant="contained" color="error" fullWidth startIcon={<StopIcon />} onClick={() => {}}>
                    Flatten All Positions
                  </Button>
                  <Button variant="outlined" color="warning" fullWidth startIcon={<SettingsIcon />} onClick={() => {}}>
                    Cancel All Orders
                  </Button>
                  <Button variant="outlined" fullWidth startIcon={<RefreshIcon />} onClick={() => {}}>
                    Refresh Data
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Order Book ({orders.length})</Typography>
              <Chip label={pendingOrders.length} color="warning" size="small" />
            </Box>
            {orders.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>No orders</Box>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Side</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Qty</TableCell>
                      <TableCell>Filled</TableCell>
                      <TableCell>Price</TableCell>
                      <TableCell>Avg Price</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orders.slice().reverse().map((order) => (
                      <TableRow key={order.id}>
                        <TableCell>{format(new Date(order.createdAt), 'HH:mm:ss')}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{order.symbol}</TableCell>
                        <TableCell>
                          <Chip label={order.side.toUpperCase()} size="small" color={order.side === 'buy' ? 'success' : 'error'} variant="outlined" />
                        </TableCell>
                        <TableCell>{order.orderType.toUpperCase()}</TableCell>
                        <TableCell>{order.quantity}</TableCell>
                        <TableCell>{order.filledQuantity}</TableCell>
                        <TableCell>{order.price ? `₹${order.price.toFixed(2)}` : 'MKT'}</TableCell>
                        <TableCell>{order.averagePrice ? `₹${order.averagePrice.toFixed(2)}` : '-'}</TableCell>
                        <TableCell>
                          <Chip
                            label={order.status.replace('_', ' ').toUpperCase()}
                            size="small"
                            color={getOrderStatusColor(order.status)}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          {['acknowledged', 'partially_filled', 'submitted'].includes(order.status) && (
                            <Button size="small" color="error" variant="outlined" onClick={() => {}}>Cancel</Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Place New Order</Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Symbol</InputLabel>
                  <Select value={orderForm.symbol} label="Symbol" onChange={(e) => setOrderForm({...orderForm, symbol: e.target.value})}>
                    <MenuItem value="NIFTY">NIFTY 50</MenuItem>
                    <MenuItem value="SENSEX">SENSEX</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Side</InputLabel>
                  <Select value={orderForm.side} label="Side" onChange={(e) => setOrderForm({...orderForm, side: e.target.value})}>
                    <MenuItem value="buy"><TrendingUpIcon sx={{ mr: 1 }} fontSize="small" />BUY</MenuItem>
                    <MenuItem value="sell"><TrendingDownIcon sx={{ mr: 1 }} fontSize="small" />SELL</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Order Type</InputLabel>
                  <Select value={orderForm.orderType} label="Order Type" onChange={(e) => setOrderForm({...orderForm, orderType: e.target.value})}>
                    <MenuItem value="market">MARKET</MenuItem>
                    <MenuItem value="limit">LIMIT</MenuItem>
                    <MenuItem value="sl">STOP LOSS</MenuItem>
                    <MenuItem value="sl_m">STOP LOSS MARKET</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Product Type</InputLabel>
                  <Select value={orderForm.productType} label="Product Type" onChange={(e) => setOrderForm({...orderForm, productType: e.target.value})}>
                    <MenuItem value="MIS">MIS (Intraday)</MenuItem>
                    <MenuItem value="NRML">NRML (Overnight)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Quantity"
                  type="number"
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm({...orderForm, quantity: parseInt(e.target.value) || 0})}
                  inputProps={{ min: 1, step: 75 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Price (LIMIT/SL)"
                  type="number"
                  value={orderForm.price}
                  onChange={(e) => setOrderForm({...orderForm, price: e.target.value})}
                  inputProps={{ step: 0.05, min: 0 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Trigger Price (SL/SL-M)"
                  type="number"
                  value={orderForm.triggerPrice}
                  onChange={(e) => setOrderForm({...orderForm, triggerPrice: e.target.value})}
                  inputProps={{ step: 0.05, min: 0 }}
                />
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                  <Button variant="outlined" onClick={() => setOrderForm({ symbol: 'NIFTY', side: 'buy', orderType: 'market', quantity: 75, price: '', triggerPrice: '', productType: 'MIS' })}>Reset</Button>
                  <Button variant="contained" color="success" size="large" onClick={handleOrderSubmit} startIcon={<PlayArrowIcon />} disabled={!isTradingEnabled}>
                    Place Order
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

const RiskStat: React.FC<{ label: string; value: string; color: 'success' | 'error' | 'warning' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="h6" sx={{ fontWeight: 600, color: `${color}.main` }}>{value}</Typography>
  </Box>
);

const FundRow: React.FC<{ label: string; value: number; color?: 'primary' | 'warning' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', color: color ? `${color}.main` : 'inherit' }}>₹{value.toLocaleString()}</Typography>
  </Box>
);

const getOrderStatusColor = (status: string) => {
  const colors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    filled: 'success',
    partially_filled: 'warning',
    acknowledged: 'info',
    submitted: 'info',
    rejected: 'error',
    cancelled: 'default',
    expired: 'default',
    created: 'default',
  };
  return colors[status] || 'default';
};

export default TradingTerminal;
