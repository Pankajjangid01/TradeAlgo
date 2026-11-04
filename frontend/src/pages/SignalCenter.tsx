import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState, addNotification } from '../store/uiSlice';
import { updateSignal } from '../store/signalsSlice';
import { api } from '../services/api';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Alert,
  Badge,
  Tabs,
  Tab,
  Skeleton,
} from '@mui/material';
import {
  FilterList as FilterListIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Pending as PendingIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';

const SignalCenter: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const signals = useSelector((state: RootState) => state.signals.signals);
  const activeSignal = useSelector((state: RootState) => state.signals.activeSignal);
  const [filterStrategy, setFilterStrategy] = useState<string[]>([]);
  const [filterDirection, setFilterDirection] = useState<string[]>([]);
  const [filterStatus, setFilterStatus] = useState<string[]>([]);
  const [selectedSignal, setSelectedSignal] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  useEffect(() => {
    dispatch(setLoadingState({ key: 'signals', loading: true }));
    const loadSignals = async () => {
      try {
        // Mock data for now
        await new Promise(resolve => setTimeout(resolve, 300));
      } catch (error) {
        console.error('Failed to load signals:', error);
      } finally {
        dispatch(setLoadingState({ key: 'signals', loading: false }));
      }
    };
    loadSignals();
  }, [dispatch]);

  const filteredSignals = signals.filter(s => {
    if (filterStrategy.length && !filterStrategy.includes(s.strategy)) return false;
    if (filterDirection.length && !filterDirection.includes(s.direction)) return false;
    if (filterStatus.length && !filterStatus.includes(s.status)) return false;
    return true;
  });

  const handleSignalClick = (signal: any) => {
    setSelectedSignal(signal);
    setDetailOpen(true);
  };

  const getStatusChip = (status: string) => {
    const configs: Record<string, { color: 'success' | 'warning' | 'error' | 'info' | 'default'; icon: React.ReactElement }> = {
      approved: { color: 'success', icon: <CheckCircleIcon fontSize="small" /> },
      order_pending: { color: 'warning', icon: <PendingIcon fontSize="small" /> },
      position_open: { color: 'info', icon: <TrendingUpIcon fontSize="small" /> },
      rejected: { color: 'error', icon: <CancelIcon fontSize="small" /> },
      closed: { color: 'default', icon: <InfoIcon fontSize="small" /> },
      wait_for_confirmation: { color: 'warning', icon: <WarningIcon fontSize="small" /> },
      watchlist: { color: 'default', icon: <InfoIcon fontSize="small" /> },
      setup_forming: { color: 'info', icon: <VisibilityIcon fontSize="small" /> },
    };
    const config = configs[status] || { color: 'default', icon: <InfoIcon fontSize="small" /> };
    return (
      <Chip
        icon={config.icon}
        label={status.replace('_', ' ').toUpperCase()}
        color={config.color}
        size="small"
        variant="outlined"
      />
    );
  };

  const getDirectionChip = (direction: string) => (
    <Chip
      label={direction.toUpperCase()}
      icon={direction === 'bullish' ? <TrendingUpIcon fontSize="small" /> : <TrendingDownIcon fontSize="small" />}
      color={direction === 'bullish' ? 'success' : 'error'}
      size="small"
      variant="outlined"
    />
  );

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Signal Center</Typography>
          <Typography variant="body2" color="text.secondary">Monitor and manage trading signals</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Strategy</InputLabel>
            <Select multiple value={filterStrategy} onChange={(e) => setFilterStrategy(e.target.value as string[])} renderValue={(v) => v.join(', ')} label="Strategy">
              <MenuItem value="orb">ORB</MenuItem>
              <MenuItem value="vwap_pullback">VWAP Pullback</MenuItem>
              <MenuItem value="sr_breakout">S/R Breakout</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Direction</InputLabel>
            <Select multiple value={filterDirection} onChange={(e) => setFilterDirection(e.target.value as string[])} renderValue={(v) => v.join(', ')} label="Direction">
              <MenuItem value="bullish">Bullish</MenuItem>
              <MenuItem value="bearish">Bearish</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Status</InputLabel>
            <Select multiple value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as string[])} renderValue={(v) => v.join(', ')} label="Status">
              <MenuItem value="watchlist">Watchlist</MenuItem>
              <MenuItem value="setup_forming">Setup Forming</MenuItem>
              <MenuItem value="wait_for_confirmation">Wait for Confirmation</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="order_pending">Order Pending</MenuItem>
              <MenuItem value="position_open">Position Open</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
              <MenuItem value="closed">Closed</MenuItem>
            </Select>
          </FormControl>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => {}}>Refresh</Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Signals Table */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Signals ({filteredSignals.length})</Typography>
                <Badge badgeContent={filteredSignals.length} color="primary" />
              </Box>
              <TableContainer sx={{ maxHeight: 600, overflow: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Instrument</TableCell>
                      <TableCell>Strategy</TableCell>
                      <TableCell>Direction</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Entry</TableCell>
                      <TableCell>Stop</TableCell>
                      <TableCell>Target</TableCell>
                      <TableCell>R:R</TableCell>
                      <TableCell>Confidence</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredSignals.map((signal) => (
                      <TableRow
                        key={signal.id}
                        hover
                        onClick={() => handleSignalClick(signal)}
                        sx={{ cursor: 'pointer', '&:last-child td': { borderBottom: 'none' } }}
                      >
                        <TableCell>{format(new Date(signal.createdAt), 'HH:mm:ss')}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{signal.instrument}</TableCell>
                        <TableCell>
                          <Chip label={signal.strategy.replace('_', ' ').toUpperCase()} size="small" variant="outlined" color="primary" />
                        </TableCell>
                        <TableCell>{getDirectionChip(signal.direction)}</TableCell>
                        <TableCell>{getStatusChip(signal.status)}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace' }}>₹{signal.entryPrice?.toFixed(2) || '-'}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', color: 'error.main' }}>₹{signal.stopPrice?.toFixed(2) || '-'}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', color: 'success.main' }}>₹{signal.targetPrice?.toFixed(2) || '-'}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{signal.rrRatio?.toFixed(2) || '-'}</TableCell>
                        <TableCell>
                          <Chip
                            label={`${(signal.confidence * 100).toFixed(0)}%`}
                            size="small"
                            color={signal.confidence > 0.7 ? 'success' : signal.confidence > 0.5 ? 'warning' : 'error'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip title="View Details">
                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleSignalClick(signal); }}>
                              <VisibilityIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filteredSignals.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={11} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                          No signals match current filters
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Signal Details Panel */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Signal Details</Typography>
              {selectedSignal ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>{selectedSignal.instrument}</Typography>
                      <Typography variant="body2" color="text.secondary">{selectedSignal.strategy.replace('_', ' ')} • {format(new Date(selectedSignal.createdAt), 'HH:mm:ss')}</Typography>
                    </Box>
                    {getDirectionChip(selectedSignal.direction)}
                  </Box>

                  <Divider />

                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                    <DetailItem label="Entry" value={`₹${selectedSignal.entryPrice?.toFixed(2) || '-'}`} />
                    <DetailItem label="Stop Loss" value={`₹${selectedSignal.stopPrice?.toFixed(2) || '-'}`} color="error" />
                    <DetailItem label="Target" value={`₹${selectedSignal.targetPrice?.toFixed(2) || '-'}`} color="success" />
                    <DetailItem label="Risk/Share" value={`₹${selectedSignal.riskPerShare?.toFixed(2) || '-'}`} />
                    <DetailItem label="Reward/Share" value={`₹${selectedSignal.rewardPerShare?.toFixed(2) || '-'}`} color="success" />
                    <DetailItem label="R:R Ratio" value={selectedSignal.rrRatio?.toFixed(2) || '-'} />
                    <DetailItem label="Confidence" value={`${(selectedSignal.confidence * 100).toFixed(0)}%`} />
                    <DetailItem label="Regime" value={selectedSignal.regimeAtSignal?.replace('_', ' ')?.toUpperCase() || '-'} />
                  </Box>

                  <Divider />

                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Indicators at Signal</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, fontSize: '0.75rem' }}>
                    {Object.entries(selectedSignal.indicators || {}).map(([key, value]) => (
                      <Box key={key} sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase' }}>{key}</Typography>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{typeof value === 'number' ? value.toFixed(2) : String(value)}</Typography>
                      </Box>
                    ))}
                  </Box>

                  <Divider />

                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>ML Prediction</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {Object.entries(selectedSignal.mlPrediction || {}).map(([key, value]) => (
                      <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary">{key}</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>{typeof value === 'number' ? value.toFixed(3) : String(value)}</Typography>
                      </Box>
                    ))}
                  </Box>

                  {selectedSignal.rejectionReason && (
                    <>
                      <Divider />
                      <Alert severity="error" sx={{ mb: 2 }}>
                        <Typography variant="caption"><strong>Rejection Reason:</strong> {selectedSignal.rejectionReason}</Typography>
                      </Alert>
                    </>
                  )}

                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Button variant="contained" color="success" size="small" disabled={selectedSignal.status !== 'approved'}>Execute</Button>
                    <Button variant="outlined" color="error" size="small" disabled={!['approved', 'wait_for_confirmation'].includes(selectedSignal.status)}>Reject</Button>
                    <Button variant="outlined" size="small" onClick={() => setDetailOpen(false)}>Close</Button>
                  </Box>
                </Box>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  Click on a signal to view details
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>{selectedSignal?.instrument} - Signal Details</DialogTitle>
        <DialogContent dividers>
          {selectedSignal && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 600 }}>
              {/* Same detail content as side panel */}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

const DetailItem: React.FC<{ label: string; value: string; color?: 'success' | 'error' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', color: color ? `${color}.main` : 'inherit' }}>{value}</Typography>
  </Box>
);

export default SignalCenter;
