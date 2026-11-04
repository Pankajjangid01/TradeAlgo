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
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  History as HistoryIcon,
  Download as DownloadIcon,
  FilterList as FilterListIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

const Backtesting: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const [activeTab, setActiveTab] = useState(0);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [runForm, setRunForm] = useState({
    name: '',
    strategy: 'orb',
    symbol: 'NIFTY',
    startDate: format(new Date(Date.now() - 30*24*60*60*1000), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
    initialCapital: 100000,
    slippage: 0.001,
    commission: 20,
  });
  const [results, setResults] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRun, setSelectedRun] = useState<any>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  const handleRunBacktest = async () => {
    try {
      dispatch(setLoadingState({ key: 'backtest', loading: true }));
      // Mock response
      await new Promise(resolve => setTimeout(resolve, 2000));
      const mockResults = generateMockResults();
      setResults(mockResults);
      setRunDialogOpen(false);
      addNotification({ type: 'success', message: 'Backtest completed successfully' });
    } catch (error: any) {
      addNotification({ type: 'error', message: error.response?.data?.detail || 'Failed to run backtest' });
    } finally {
      dispatch(setLoadingState({ key: 'backtest', loading: false }));
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ maxWidth: '100%' }}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>Backtesting</Typography>
            <Typography variant="body2" color="text.secondary">Test strategies on historical data</Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<HistoryIcon />} onClick={() => setRunDialogOpen(true)}>New Backtest</Button>
            <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={handleRunBacktest} disabled={activeTab !== 0}>Run</Button>
          </Box>
        </Box>

        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v as number)} sx={{ mb: 3 }}>
          <Tab label="Run Backtest" icon={<PlayArrowIcon />} />
          <Tab label="Results History" icon={<HistoryIcon />} />
          <Tab label="Analytics" icon={<AnalyticsIcon />} />
        </Tabs>

        {activeTab === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} lg={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Backtest Configuration</Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" label="Name" value={runForm.name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, name: e.target.value})} placeholder="My ORB Strategy Test" />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Strategy</InputLabel>
                        <Select value={runForm.strategy} label="Strategy" onChange={(e) => setRunForm({...runForm, strategy: e.target.value})}>
                          <MenuItem value="orb">Opening Range Breakout</MenuItem>
                          <MenuItem value="vwap_pullback">VWAP Pullback</MenuItem>
                          <MenuItem value="sr_breakout">S/R Breakout & Retest</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Symbol</InputLabel>
                        <Select value={runForm.symbol} label="Symbol" onChange={(e) => setRunForm({...runForm, symbol: e.target.value})}>
                          <MenuItem value="NIFTY">NIFTY 50</MenuItem>
                          <MenuItem value="SENSEX">SENSEX</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" type="number" label="Initial Capital (₹)" value={runForm.initialCapital} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, initialCapital: parseInt(e.target.value)})} inputProps={{ min: 10000, step: 10000 }} />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" type="date" label="Start Date" value={runForm.startDate} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, startDate: e.target.value})} InputLabelProps={{ shrink: true }} />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" type="date" label="End Date" value={runForm.endDate} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, endDate: e.target.value})} InputLabelProps={{ shrink: true }} />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" label="Slippage %" type="number" value={runForm.slippage} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, slippage: parseFloat(e.target.value)})} inputProps={{ min: 0, max: 0.01, step: 0.0001 }} />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField fullWidth size="small" label="Commission per Lot (₹)" type="number" value={runForm.commission} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, commission: parseInt(e.target.value)})} inputProps={{ min: 0, step: 1 }} />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} lg={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Strategy Parameters</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>ORB Parameters</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <TextField fullWidth size="small" label="Opening Range Minutes" type="number" value={15} inputProps={{ min: 5, max: 60, step: 5 }} />
                          <TextField fullWidth size="small" label="Min Relative Volume" type="number" value={1.5} inputProps={{ min: 0.5, max: 5, step: 0.1 }} />
                          <FormControl fullWidth size="small">
                            <InputLabel>Stop Method</InputLabel>
                            <Select value="or_mid" label="Stop Method">
                              <MenuItem value="or_mid">OR Mid</MenuItem>
                              <MenuItem value="or_low">OR Low</MenuItem>
                              <MenuItem value="atr">ATR Based</MenuItem>
                            </Select>
                          </FormControl>
                          <TextField fullWidth size="small" label="Target R Multiple" type="number" value={2} inputProps={{ min: 1, max: 5, step: 0.5 }} />
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Risk Management</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <TextField fullWidth size="small" label="Risk Per Trade %" type="number" value={0.35} inputProps={{ min: 0.1, max: 2, step: 0.05 }} />
                          <TextField fullWidth size="small" label="Max Daily Loss %" type="number" value={1.25} inputProps={{ min: 0.5, max: 5, step: 0.1 }} />
                          <TextField fullWidth size="small" label="Max Positions" type="number" value={1} inputProps={{ min: 1, max: 5, step: 1 }} />
                          <TextField fullWidth size="small" label="Max Consecutive Losses" type="number" value={3} inputProps={{ min: 1, max: 10, step: 1 }} />
                        </Box>
                      </AccordionDetails>
                    </Accordion>
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
                <Typography variant="h6" sx={{ fontWeight: 600 }}>Backtest Runs</Typography>
                <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => {}}>Refresh</Button>
              </Box>
              {runs.length === 0 && results ? (
                <>
                  <Alert severity="info">
                    Last run completed. Click "Run" to see results here.
                  </Alert>
                </>
              ) : runs.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>No backtest runs yet</Box>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Strategy</TableCell>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Period</TableCell>
                        <TableCell>Trades</TableCell>
                        <TableCell>Win Rate</TableCell>
                        <TableCell>Net P&L</TableCell>
                        <TableCell>Max DD</TableCell>
                        <TableCell>Sharpe</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {runs.map((run) => (
                        <TableRow key={run.id} hover onClick={(e) => { e.stopPropagation(); setSelectedRun(run); setDetailDialogOpen(true); }}>
                          <TableCell sx={{ fontWeight: 600 }}>{run.name}</TableCell>
                          <TableCell>{run.strategy}</TableCell>
                          <TableCell>{run.symbol}</TableCell>
                          <TableCell>{`${format(new Date(run.startDate), 'MMM dd')} - ${format(new Date(run.endDate), 'MMM dd')}`}</TableCell>
                          <TableCell>{run.totalTrades}</TableCell>
                          <TableCell>{`${run.winRate.toFixed(1)}%`}</TableCell>
                          <TableCell sx={{ fontWeight: 600, color: run.netPnl >= 0 ? 'success.main' : 'error.main' }}>₹{run.netPnl.toLocaleString()}</TableCell>
                          <TableCell>{`${run.maxDrawdown.toFixed(1)}%`}</TableCell>
                          <TableCell>{run.sharpeRatio?.toFixed(2) || '-'}</TableCell>
                          <TableCell>
                            <Button size="small" onClick={(e) => { e.stopPropagation(); setSelectedRun(run); setDetailDialogOpen(true); }}>View</Button>
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

        {activeTab === 2 && results && (
          <Grid container spacing={3}>
            <Grid item xs={12} lg={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Equity Curve</Typography>
                  <Box sx={{ height: 400 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={results.equityCurve}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00d4aa" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#00d4aa" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                        <XAxis dataKey="date" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} />
                        <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} tickFormatter={val => `₹${val.toLocaleString()}`} />
                        <Tooltip />
                        <Area type="monotone" dataKey="equity" stroke="#00d4aa" fillOpacity={1} fill="url(#colorEquity)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} lg={4}>
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Performance Summary</Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    <PerfRow label="Total Trades" value={results.totalTrades} />
                    <PerfRow label="Win Rate" value={`${results.winRate.toFixed(1)}%`} color={results.winRate > 50 ? 'success' : 'error'} />
                    <PerfRow label="Profit Factor" value={results.profitFactor.toFixed(2)} color={results.profitFactor > 1 ? 'success' : 'error'} />
                    <PerfRow label="Expectancy" value={`₹${results.expectancy.toFixed(0)}`} color={results.expectancy > 0 ? 'success' : 'error'} />
                    <PerfRow label="Net P&L" value={`₹${results.netPnl.toLocaleString()}`} color={results.netPnl >= 0 ? 'success' : 'error'} />
                    <PerfRow label="Max Drawdown" value={`${results.maxDrawdown.toFixed(1)}%`} color={results.maxDrawdown < 10 ? 'success' : results.maxDrawdown < 20 ? 'warning' : 'error'} />
                    <PerfRow label="Sharpe Ratio" value={results.sharpeRatio?.toFixed(2) || 'N/A'} color={results.sharpeRatio && results.sharpeRatio > 1 ? 'success' : 'warning'} />
                    <PerfRow label="Sortino Ratio" value={results.sortinoRatio?.toFixed(2) || 'N/A'} />
                    <PerfRow label="Avg Hold Time" value={results.avgHoldTime || 'N/A'} />
                    <PerfRow label="Max Consecutive Wins" value={results.maxConsecWins || 0} color="success" />
                    <PerfRow label="Max Consecutive Losses" value={results.maxConsecLosses || 0} color="error" />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Run Dialog */}
        <Dialog open={runDialogOpen} onClose={() => setRunDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>New Backtest Run</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" label="Name" value={runForm.name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, name: e.target.value})} placeholder="My Strategy Test" />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Strategy</InputLabel>
                  <Select value={runForm.strategy} label="Strategy" onChange={(e) => setRunForm({...runForm, strategy: e.target.value})}>
                    <MenuItem value="orb">Opening Range Breakout</MenuItem>
                    <MenuItem value="vwap_pullback">VWAP Pullback</MenuItem>
                    <MenuItem value="sr_breakout">S/R Breakout & Retest</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Symbol</InputLabel>
                  <Select value={runForm.symbol} label="Symbol" onChange={(e) => setRunForm({...runForm, symbol: e.target.value})}>
                    <MenuItem value="NIFTY">NIFTY 50</MenuItem>
                    <MenuItem value="SENSEX">SENSEX</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" type="number" label="Initial Capital (₹)" value={runForm.initialCapital} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, initialCapital: parseInt(e.target.value)})} inputProps={{ min: 10000, step: 10000 }} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" type="date" label="Start Date" value={runForm.startDate} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, startDate: e.target.value})} InputLabelProps={{ shrink: true }} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField fullWidth size="small" type="date" label="End Date" value={runForm.endDate} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRunForm({...runForm, endDate: e.target.value})} InputLabelProps={{ shrink: true }} />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRunDialogOpen(false)}>Cancel</Button>
            <Button variant="contained" color="primary" onClick={() => { setRunDialogOpen(false); handleRunBacktest(); }}>Run Backtest</Button>
          </DialogActions>
        </Dialog>

        {/* Detail Dialog */}
        <Dialog open={detailDialogOpen} onClose={() => setDetailDialogOpen(false)} maxWidth="lg" fullWidth>
          <DialogTitle>{selectedRun?.name} - Details</DialogTitle>
          <DialogContent dividers>
            {selectedRun && (
              <Box sx={{ minWidth: 600 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>Trade List</Typography>
                <TableContainer sx={{ maxHeight: 400 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Entry Time</TableCell>
                        <TableCell>Exit Time</TableCell>
                        <TableCell>Side</TableCell>
                        <TableCell>Entry</TableCell>
                        <TableCell>Exit</TableCell>
                        <TableCell>P&L</TableCell>
                        <TableCell>R-Multiple</TableCell>
                        <TableCell>Exit Reason</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedRun.trades?.slice(0, 50).map((trade: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell>{format(new Date(trade.entryTime), 'MMM dd HH:mm')}</TableCell>
                          <TableCell>{trade.exitTime ? format(new Date(trade.exitTime), 'MMM dd HH:mm') : '-'}</TableCell>
                          <TableCell>
                            <Chip label={trade.direction.toUpperCase()} size="small" color={trade.direction === 'bullish' ? 'success' : 'error'} variant="outlined" />
                          </TableCell>
                          <TableCell>₹{trade.entryPrice.toFixed(2)}</TableCell>
                          <TableCell>₹{trade.exitPrice?.toFixed(2) || '-'}</TableCell>
                          <TableCell sx={{ fontWeight: 600, color: trade.pnl >= 0 ? 'success.main' : 'error.main' }}>₹{trade.pnl?.toFixed(2) || '-'}</TableCell>
                          <TableCell>{trade.rMultiple?.toFixed(2) || '-'}</TableCell>
                          <TableCell>{trade.exitReason || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

const PerfRow: React.FC<{ label: string; value: string; color?: 'success' | 'error' | 'warning' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', color: color ? `${color}.main` : 'inherit' }}>{value}</Typography>
  </Box>
);

const generateMockResults = () => ({
  totalTrades: 156,
  winRate: 54.5,
  profitFactor: 1.42,
  expectancy: 245,
  netPnl: 38220,
  maxDrawdown: 8.5,
  sharpeRatio: 1.34,
  sortinoRatio: 1.87,
  avgHoldTime: '2h 15m',
  maxConsecWins: 7,
  maxConsecLosses: 4,
  equityCurve: Array.from({ length: 100 }, (_, i) => ({
    date: format(new Date(Date.now() - (99-i)*24*60*60*1000), 'MMM dd'),
    equity: 100000 + Math.random() * 50000 + i * 382,
  })),
});

export default Backtesting;
