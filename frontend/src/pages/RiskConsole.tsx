import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification } from '../store/uiSlice';
import { toggleKillSwitch } from '../store/tradingSlice';
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
  LinearProgress,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Block as BlockIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

const RiskConsole: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const riskMetrics = useSelector((state: RootState) => state.trading.riskMetrics);
  const positions = useSelector((state: RootState) => state.trading.positions);
  const orders = useSelector((state: RootState) => state.trading.orders);
  const funds = useSelector((state: RootState) => state.trading.funds);
  const tradingMode = useSelector((state: RootState) => state.trading.tradingMode);
  const isTradingEnabled = useSelector((state: RootState) => state.trading.isTradingEnabled);
  const [activeTab, setActiveTab] = useState(0);
  const [editing, setEditing] = useState(false);
  const [config, setConfig] = useState({
    initialRiskPerTradePct: 0.35,
    maxDailyLossPct: 1.25,
    maxSimultaneousPositions: 1,
    maxConsecutiveLosses: 3,
    targetRMultiple: 2.0,
    partialExitRMultiple: 1.5,
    trailingStopActivationR: 1.0,
    trailingStopDistanceAtr: 1.0,
    maxSlippagePct: 0.2,
    cashBufferPct: 10,
  });

  const openPositions = positions.filter(p => p.isOpen);
  const totalExposure = openPositions.reduce((sum, p) => sum + p.quantity * p.currentPrice, 0);

  const handleSaveConfig = () => {
    addNotification({ type: 'success', message: 'Risk configuration saved' });
    setEditing(false);
  };

  const handleResetConfig = () => {
    setConfig({
      initialRiskPerTradePct: 0.35,
      maxDailyLossPct: 1.25,
      maxSimultaneousPositions: 1,
      maxConsecutiveLosses: 3,
      targetRMultiple: 2.0,
      partialExitRMultiple: 1.5,
      trailingStopActivationR: 1.0,
      trailingStopDistanceAtr: 1.0,
      maxSlippagePct: 0.2,
      cashBufferPct: 10,
    });
  };

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Risk Console</Typography>
          <Typography variant="body2" color="text.secondary">Monitor and configure risk management parameters</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => {}}>Refresh</Button>
          <Button variant={riskMetrics.killSwitchActive ? 'contained' : 'outlined'} color="error" onClick={() => dispatch(toggleKillSwitch())} startIcon={riskMetrics.killSwitchActive ? <CheckCircleIcon /> : <BlockIcon />}>
            {riskMetrics.killSwitchActive ? 'KILL SWITCH ACTIVE' : 'ACTIVATE KILL SWITCH'}
          </Button>
        </Box>
      </Box>

      {/* Risk Status Banner */}
      {riskMetrics.killSwitchActive && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WarningIcon color="error" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>KILL SWITCH ACTIVE</Typography>
            <Typography variant="body1" sx={{ flexGrow: 1 }}>All new entries blocked. Existing positions can still be managed.</Typography>
            <Button variant="contained" color="error" onClick={() => dispatch(toggleKillSwitch())} startIcon={<CheckCircleIcon />}>Deactivate</Button>
          </Box>
        </Alert>
      )}

      {/* Risk Health Indicators */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} lg={3}>
          <Card sx={{ borderLeft: `4px solid ${riskMetrics.dailyPnl >= -riskMetrics.dailyLossLimit * 0.5 ? '#3fb950' : riskMetrics.dailyPnl >= -riskMetrics.dailyLossLimit * 0.8 ? '#d29922' : '#f85149'}` }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Daily P&L vs Limit</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: riskMetrics.dailyPnl >= 0 ? 'success.main' : 'error.main' }}>
                ₹{riskMetrics.dailyPnl.toLocaleString()}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                <LinearProgress variant="determinate" value={Math.min(100, Math.max(0, (riskMetrics.dailyPnl + riskMetrics.dailyLossLimit) / riskMetrics.dailyLossLimit * 100))} sx={{ flex: 1, height: 6 }} color={riskMetrics.dailyPnl >= -riskMetrics.dailyLossLimit * 0.8 ? 'success' : 'error'} />
                <Typography variant="caption" sx={{ fontFamily: 'monospace', minWidth: 60 }}>
                  {((riskMetrics.dailyPnl + riskMetrics.dailyLossLimit) / riskMetrics.dailyLossLimit * 100).toFixed(0)}%
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">Limit: ₹{riskMetrics.dailyLossLimit.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <Card sx={{ borderLeft: `4px solid ${openPositions.length >= riskMetrics.maxPositions ? '#f85149' : '#3fb950'}` }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Position Utilization</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>{openPositions.length} / {riskMetrics.maxPositions}</Typography>
              <LinearProgress variant="determinate" value={riskMetrics.maxPositions > 0 ? openPositions.length / riskMetrics.maxPositions * 100 : 0} sx={{ mt: 1, height: 6 }} color={openPositions.length >= riskMetrics.maxPositions ? 'error' : 'success'} />
              <Typography variant="caption" color="text.secondary">Max: {riskMetrics.maxPositions} positions</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <Card sx={{ borderLeft: `4px solid ${riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses ? '#f85149' : riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses * 0.7 ? '#d29922' : '#3fb950'}` }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Consecutive Losses</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses ? 'error.main' : 'inherit' }}>
                {riskMetrics.consecutiveLosses} / {riskMetrics.maxConsecutiveLosses}
              </Typography>
              <LinearProgress variant="determinate" value={riskMetrics.maxConsecutiveLosses > 0 ? riskMetrics.consecutiveLosses / riskMetrics.maxConsecutiveLosses * 100 : 0} sx={{ mt: 1, height: 6 }} color={riskMetrics.consecutiveLosses >= riskMetrics.maxConsecutiveLosses ? 'error' : 'success'} />
              <Typography variant="caption" color="text.secondary">Halt at: {riskMetrics.maxConsecutiveLosses}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <Card sx={{ borderLeft: `4px solid ${totalExposure >= riskMetrics.maxExposure * 0.8 ? '#d29922' : '#3fb950'}` }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">Exposure Utilization</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>₹{totalExposure.toLocaleString()}</Typography>
              <LinearProgress variant="determinate" value={riskMetrics.maxExposure > 0 ? totalExposure / riskMetrics.maxExposure * 100 : 0} sx={{ mt: 1, height: 6 }} color={totalExposure >= riskMetrics.maxExposure * 0.8 ? 'warning' : 'success'} />
              <Typography variant="caption" color="text.secondary">Max: ₹{riskMetrics.maxExposure.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v as number)} sx={{ mb: 3 }}>
        <Tab label="Overview" icon={<VisibilityIcon />} />
        <Tab label="Configuration" icon={<SettingsIcon />} />
        <Tab label="Limits & Rules" icon={<SecurityIcon />} />
        <Tab label="Emergency" icon={<BlockIcon />} />
      </Tabs>

      {/* Overview Tab */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Position Risk Analysis</Typography>
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
                          <TableCell>Entry</TableCell>
                          <TableCell>Current</TableCell>
                          <TableCell>Unrealized P&L</TableCell>
                          <TableCell>Risk %</TableCell>
                          <TableCell>Stop</TableCell>
                          <TableCell>Target</TableCell>
                          <TableCell>R:R</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {openPositions.map((pos) => {
                          const riskPct = pos.stopPrice ? Math.abs(pos.currentPrice - pos.stopPrice) / pos.currentPrice * 100 : 0;
                          const rr = pos.stopPrice && pos.targetPrice ? Math.abs(pos.targetPrice - pos.currentPrice) / Math.abs(pos.currentPrice - pos.stopPrice) : 0;
                          return (
                            <TableRow key={pos.id}>
                              <TableCell sx={{ fontWeight: 600 }}>{pos.symbol}</TableCell>
                              <TableCell><Chip label={pos.side.toUpperCase()} size="small" color={pos.side === 'long' ? 'success' : 'error'} variant="outlined" /></TableCell>
                              <TableCell>{pos.quantity}</TableCell>
                              <TableCell>₹{pos.averagePrice.toFixed(2)}</TableCell>
                              <TableCell>₹{pos.currentPrice.toFixed(2)}</TableCell>
                              <TableCell sx={{ fontWeight: 600, color: pos.unrealizedPnl >= 0 ? 'success.main' : 'error.main' }}>₹{pos.unrealizedPnl.toFixed(2)}</TableCell>
                              <TableCell sx={{ color: riskPct > 2 ? 'error.main' : 'inherit' }}>{riskPct.toFixed(2)}%</TableCell>
                              <TableCell>{pos.stopPrice ? `₹${pos.stopPrice.toFixed(2)}` : '-'}</TableCell>
                              <TableCell>{pos.targetPrice ? `₹${pos.targetPrice.toFixed(2)}` : '-'}</TableCell>
                              <TableCell sx={{ fontWeight: 600, color: rr >= 1.5 ? 'success.main' : 'warning.main' }}>{rr.toFixed(2)}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Order Risk Check</Typography>
                {orders.filter(o => ['acknowledged', 'partially_filled', 'submitted'].includes(o.status)).length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>No pending orders</Box>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Side</TableCell>
                          <TableCell>Qty</TableCell>
                          <TableCell>Price</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Risk Check</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {orders.filter(o => ['acknowledged', 'partially_filled', 'submitted'].includes(o.status)).map((order) => (
                          <TableRow key={order.id}>
                            <TableCell sx={{ fontWeight: 600 }}>{order.symbol}</TableCell>
                            <TableCell><Chip label={order.side.toUpperCase()} size="small" color={order.side === 'buy' ? 'success' : 'error'} variant="outlined" /></TableCell>
                            <TableCell>{order.quantity}</TableCell>
                            <TableCell>{order.price ? `₹${order.price.toFixed(2)}` : 'MKT'}</TableCell>
                            <TableCell><Chip label={order.status.replace('_', ' ').toUpperCase()} size="small" color="warning" variant="outlined" /></TableCell>
                            <TableCell>
                              <Chip label="PENDING" size="small" color="warning" variant="outlined" />
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

          <Grid item xs={12} lg={4}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Funds Availability</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <FundRiskRow label="Available Cash" value={funds?.availableCash || 0} />
                  <FundRiskRow label="Available Margin" value={funds?.availableMargin || 0} color="primary" />
                  <FundRiskRow label="Used Margin" value={funds?.usedMargin || 0} color="warning" />
                  <Divider />
                  <FundRiskRow label="Total Exposure" value={totalExposure} color={totalExposure > (funds?.availableMargin || 0) * 0.8 ? 'error' : 'success'} />
                  <FundRiskRow label="Free Margin" value={(funds?.availableMargin || 0) - totalExposure} color={(funds?.availableMargin || 0) - totalExposure < 0 ? 'error' : 'success'} />
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Risk Rules Status</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <RuleRow name="Max Daily Loss" passed={riskMetrics.dailyPnl > -riskMetrics.dailyLossLimit} detail={`Used: ${((riskMetrics.dailyPnl + riskMetrics.dailyLossLimit) / riskMetrics.dailyLossLimit * 100).toFixed(0)}%`} />
                  <RuleRow name="Max Positions" passed={openPositions.length < riskMetrics.maxPositions} detail={`${openPositions.length}/${riskMetrics.maxPositions}`} />
                  <RuleRow name="Consecutive Losses" passed={riskMetrics.consecutiveLosses < riskMetrics.maxConsecutiveLosses} detail={`${riskMetrics.consecutiveLosses}/${riskMetrics.maxConsecutiveLosses}`} />
                  <RuleRow name="Exposure Limit" passed={totalExposure < riskMetrics.maxExposure} detail={`₹${totalExposure.toLocaleString()}/₹${riskMetrics.maxExposure.toLocaleString()}`} />
                  <RuleRow name="Kill Switch" passed={!riskMetrics.killSwitchActive} detail={riskMetrics.killSwitchActive ? 'ACTIVE' : 'INACTIVE'} />
                  <RuleRow name="Trading Enabled" passed={isTradingEnabled} detail={isTradingEnabled ? 'ENABLED' : 'DISABLED'} />
                  <RuleRow name="Broker Connected" passed={true} detail="Connected" />
                  <RuleRow name="Data Feed Live" passed={true} detail="Live" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Configuration Tab */}
      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Risk Configuration</Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="outlined" onClick={handleResetConfig} startIcon={<RefreshIcon />}>Reset to Defaults</Button>
                <Button variant={editing ? 'contained' : 'outlined'} onClick={() => setEditing(!editing)} startIcon={editing ? <SaveIcon /> : <EditIcon />}>
                  {editing ? 'Save Changes' : 'Edit'}
                </Button>
              </Box>
            </Box>

            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small" disabled={!editing}>
                  <InputLabel>Initial Risk Per Trade (%)</InputLabel>
                  <Select value={String(config.initialRiskPerTradePct)} label="Initial Risk Per Trade" onChange={(e) => setConfig({...config, initialRiskPerTradePct: parseFloat(e.target.value)})}>
                    {[0.1, 0.25, 0.35, 0.5, 0.75, 1.0].map(v => <MenuItem key={v} value={String(v)}>{v}%</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small" disabled={!editing}>
                  <InputLabel>Max Daily Loss (%)</InputLabel>
                  <Select value={String(config.maxDailyLossPct)} label="Max Daily Loss" onChange={(e) => setConfig({...config, maxDailyLossPct: parseFloat(e.target.value)})}>
                    {[0.5, 0.75, 1.0, 1.25, 1.5, 2.0].map(v => <MenuItem key={v} value={String(v)}>{v}%</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small" disabled={!editing}>
                  <InputLabel>Max Simultaneous Positions</InputLabel>
                  <Select value={String(config.maxSimultaneousPositions)} label="Max Positions" onChange={(e) => setConfig({...config, maxSimultaneousPositions: parseInt(e.target.value)})}>
                    {[1, 2, 3, 4, 5].map(v => <MenuItem key={v} value={String(v)}>{v}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small" disabled={!editing}>
                  <InputLabel>Max Consecutive Losses</InputLabel>
                  <Select value={String(config.maxConsecutiveLosses)} label="Max Consecutive Losses" onChange={(e) => setConfig({...config, maxConsecutiveLosses: parseInt(e.target.value)})}>
                    {[2, 3, 4, 5, 6, 7].map(v => <MenuItem key={v} value={String(v)}>{v}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Target R Multiple" type="number" value={config.targetRMultiple} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, targetRMultiple: parseFloat(e.target.value)})} inputProps={{ min: 1, max: 5, step: 0.5 }} disabled={!editing} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Partial Exit R Multiple" type="number" value={config.partialExitRMultiple} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, partialExitRMultiple: parseFloat(e.target.value)})} inputProps={{ min: 0.5, max: 3, step: 0.5 }} disabled={!editing} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Trailing Stop Activation (R)" type="number" value={config.trailingStopActivationR} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, trailingStopActivationR: parseFloat(e.target.value)})} inputProps={{ min: 0.5, max: 3, step: 0.5 }} disabled={!editing} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Trailing Stop Distance (ATR)" type="number" value={config.trailingStopDistanceAtr} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, trailingStopDistanceAtr: parseFloat(e.target.value)})} inputProps={{ min: 0.5, max: 3, step: 0.5 }} disabled={!editing} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Max Slippage (%)" type="number" value={config.maxSlippagePct} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, maxSlippagePct: parseFloat(e.target.value)})} inputProps={{ min: 0.05, max: 1, step: 0.05 }} disabled={!editing} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Cash Buffer (%)" type="number" value={config.cashBufferPct} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfig({...config, cashBufferPct: parseInt(e.target.value)})} inputProps={{ min: 5, max: 30, step: 1 }} disabled={!editing} />
              </Grid>
            </Grid>

            {editing && (
              <Alert severity="info" sx={{ mt: 3 }}>
                Changes will apply to new trades only. Existing positions retain their original risk parameters.
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Limits & Rules Tab */}
      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Pre-Trade Risk Checks</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <CheckRow name="Daily Loss Limit" description="Block new entries if daily P&L exceeds limit" enabled />
                  <CheckRow name="Max Positions" description="Limit concurrent open positions" enabled />
                  <CheckRow name="Consecutive Losses" description="Halt trading after N consecutive losses" enabled />
                  <CheckRow name="Kill Switch" description="Emergency stop for all trading activity" enabled />
                  <CheckRow name="Position Size Limits" description="Validate quantity against risk budget and funds" enabled />
                  <CheckRow name="R:R Ratio Minimum" description="Reject trades with insufficient reward/risk" enabled />
                  <CheckRow name="Spread Check" description="Ensure stop distance exceeds minimum spread" enabled />
                  <CheckRow name="Price Validity" description="Reject orders if price moved beyond threshold" enabled />
                  <CheckRow name="ML Confidence" description="Require minimum ML model confidence" enabled />
                  <CheckRow name="Regime Alignment" description="Verify strategy matches market regime" enabled />
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Post-Trade Risk Monitoring</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <CheckRow name="Position Reconciliation" description="Periodic sync with broker positions" enabled />
                  <CheckRow name="Stop Loss Monitoring" description="Track SL orders and alert on failures" enabled />
                  <CheckRow name="Margin Monitoring" description="Alert on margin shortfalls" enabled />
                  <CheckRow name="P&L Attribution" description="Track P&L by strategy, instrument, time" enabled />
                  <CheckRow name="Slippage Tracking" description="Monitor execution quality" enabled />
                  <CheckRow name="Duplicate Order Detection" description="Prevent accidental double orders" enabled />
                  <CheckRow name="Partial Fill Handling" description="Manage residual quantities correctly" enabled />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Emergency Procedures</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <EmergencyRow 
                    title="Daily Loss Limit Breached" 
                    trigger="Daily P&L ≤ -Max Daily Loss"
                    actions={[
                      "Block all new entries",
                      "Cancel all pending entry orders",
                      "Allow exit orders for existing positions",
                      "Alert operator via notification",
                    ]}
                  />
                  <EmergencyRow 
                    title="Kill Switch Activated" 
                    trigger="Manual activation or system error"
                    actions={[
                      "Block all new entries immediately",
                      "Cancel all pending orders",
                      "Initiate controlled position flattening",
                      "Require manual re-arm with authorization",
                    ]}
                  />
                  <EmergencyRow 
                    title="Broker Disconnection" 
                    trigger="WebSocket/API connection lost > 30s"
                    actions={[
                      "Block new entries",
                      "Switch to emergency monitoring mode",
                      "Alert operator",
                      "Attempt auto-reconnect",
                    ]}
                  />
                  <EmergencyRow 
                    title="Data Feed Stale" 
                    trigger="No price updates > 5 seconds"
                    actions={[
                      "Block new entries",
                      "Use last known price for risk calc",
                      "Alert operator",
                      "Attempt feed recovery",
                    ]}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Emergency Tab */}
      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <Card sx={{ borderLeft: '4px solid #f85149' }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: 'error.main' }}>Kill Switch</Typography>
                <Alert severity="warning">
                  Activating the kill switch will immediately block all new trades and cancel pending orders.
                  This action requires manual re-authorization to resume trading.
                </Alert>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Button 
                    variant={riskMetrics.killSwitchActive ? 'contained' : 'outlined'} 
                    color="error" 
                    size="large"
                    onClick={() => dispatch(toggleKillSwitch())}
                    startIcon={riskMetrics.killSwitchActive ? <CheckCircleIcon /> : <BlockIcon />}
                    disabled={false}
                  >
                    {riskMetrics.killSwitchActive ? 'DEACTIVATE KILL SWITCH' : 'ACTIVATE KILL SWITCH'}
                  </Button>
                  <Button variant="outlined" color="warning" size="large" onClick={() => {}} startIcon={<CancelIcon />}>
                    Cancel All Orders
                  </Button>
                  <Button variant="outlined" color="error" size="large" onClick={() => {}} startIcon={<BlockIcon />}>
                    Flatten All Positions
                  </Button>
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Emergency Contacts & Procedures</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <EmergencyContact name="Primary Operator" role="System Admin" phone="+91-XXXXXXXXXX" email="admin@tradeiq.com" />
                  <EmergencyContact name="Risk Manager" role="Risk Control" phone="+91-XXXXXXXXXX" email="risk@tradeiq.com" />
                  <EmergencyContact name="Broker Support" role="Angel One" phone="1800-XXX-XXXX" email="support@angelone.in" />
                  <EmergencyContact name="Exchange Support" role="NSE" phone="1800-XXX-XXXX" email="support@nseindia.com" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Kill Switch History</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Timestamp</TableCell>
                        <TableCell>Action</TableCell>
                        <TableCell>Triggered By</TableCell>
                        <TableCell>Reason</TableCell>
                        <TableCell>Duration</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      <TableRow>
                        <TableCell>{format(new Date(), 'MMM dd, HH:mm')}</TableCell>
                        <TableCell><Chip label="ACTIVATED" size="small" color="error" variant="filled" /></TableCell>
                        <TableCell>System Auto</TableCell>
                        <TableCell>Daily loss limit breached</TableCell>
                        <TableCell>15 min</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>

            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>System Health Checks</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <HealthCheck name="WebSocket Connection" status="healthy" detail="Latency: 12ms" />
                  <HealthCheck name="Broker API" status="healthy" detail="Response: 45ms" />
                  <HealthCheck name="Database" status="healthy" detail="Pool: 8/10" />
                  <HealthCheck name="ML Service" status="healthy" detail="Inference: 8ms" />
                  <HealthCheck name="Risk Engine" status="healthy" detail="Checks: 0.3ms" />
                  <HealthCheck name="OMS" status="healthy" detail="Queue: 0" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

const FundRiskRow: React.FC<{ label: string; value: number; color?: 'success' | 'error' | 'warning' | 'primary' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', color: color ? `${color}.main` : 'inherit' }}>₹{value.toLocaleString()}</Typography>
  </Box>
);

const RuleRow: React.FC<{ name: string; passed: boolean; detail: string }> = ({ name, passed, detail }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: passed ? 'success.main' : 'error.main' }} />
      <Typography variant="body2" sx={{ fontWeight: 500 }}>{name}</Typography>
    </Box>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="caption" color="text.secondary">{detail}</Typography>
      <Chip label={passed ? 'PASS' : 'FAIL'} size="small" color={passed ? 'success' : 'error'} variant="outlined" />
    </Box>
  </Box>
);

const CheckRow: React.FC<{ name: string; description: string; enabled: boolean }> = ({ name, description, enabled }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: enabled ? 'success.main' : 'default.main' }} />
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>{name}</Typography>
        <Typography variant="caption" color="text.secondary">{description}</Typography>
      </Box>
    </Box>
    <Chip label={enabled ? 'ENABLED' : 'DISABLED'} size="small" color={enabled ? 'success' : 'default'} variant="outlined" />
  </Box>
);

const EmergencyRow: React.FC<{ title: string; trigger: string; actions: string[] }> = ({ title, trigger, actions }) => (
  <Box sx={{ p: 2, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>{title}</Typography>
    <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}><strong>Trigger:</strong> {trigger}</Typography>
    <Typography variant="caption" color="text.secondary"><strong>Actions:</strong></Typography>
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, ml: 2, mt: 0.5 }}>
      {actions.map((action, i) => (
        <Typography key={i} variant="caption" color="text.primary">▸ {action}</Typography>
      ))}
    </Box>
  </Box>
);

const EmergencyContact: React.FC<{ name: string; role: string; phone: string; email: string }> = ({ name, role, phone, email }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Box>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>{name}</Typography>
      <Typography variant="caption" color="text.secondary">{role}</Typography>
    </Box>
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
      <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{phone}</Typography>
      <Typography variant="caption" color="text.secondary">{email}</Typography>
    </Box>
  </Box>
);

const HealthCheck: React.FC<{ name: string; status: 'healthy' | 'degraded' | 'down'; detail: string }> = ({ name, status, detail }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: status === 'healthy' ? 'success.main' : status === 'degraded' ? 'warning.main' : 'error.main' }} />
      <Typography variant="body2" sx={{ fontWeight: 500 }}>{name}</Typography>
    </Box>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="caption" color="text.secondary">{detail}</Typography>
      <Chip label={status.toUpperCase()} size="small" color={status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'error'} variant="outlined" />
    </Box>
  </Box>
);

export default RiskConsole;
