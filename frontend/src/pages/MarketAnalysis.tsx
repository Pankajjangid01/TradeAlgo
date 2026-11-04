import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import { setLoadingState } from '../store/uiSlice';
import { setSelectedInstrument, setSelectedTimeframe } from '../store/marketSlice';
import { api } from '../services/api';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Divider,
  Skeleton,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  ShowChart as ShowChartIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

const MarketAnalysis: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { selectedInstrument, selectedTimeframe, candles, isConnected } = useSelector((state: RootState) => state.market);
  const signals = useSelector((state: RootState) => state.signals.signals);
  const [activeTab, setActiveTab] = useState(0);
  const [indicators, setIndicators] = useState<any>({});
  const [structure, setStructure] = useState<any>({});
  const [regime, setRegime] = useState<any>({});

  useEffect(() => {
    dispatch(setLoadingState({ key: 'market-analysis', loading: true }));
    const loadData = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, 500));
        setIndicators(generateMockIndicators());
        setStructure(generateMockStructure());
        setRegime(generateMockRegime());
      } catch (error) {
        console.error('Failed to load market analysis:', error);
      } finally {
        dispatch(setLoadingState({ key: 'market-analysis', loading: false }));
      }
    };
    loadData();
  }, [selectedInstrument, selectedTimeframe, dispatch]);

  const instrumentCandles = candles[`${selectedInstrument}_${selectedTimeframe}`] || [];
  const currentPrice = instrumentCandles.length > 0 ? instrumentCandles[instrumentCandles.length - 1].close : 0;

  const handleInstrumentChange = (event: any) => {
    dispatch(setSelectedInstrument(event.target.value));
  };

  const handleTimeframeChange = (event: any) => {
    dispatch(setSelectedTimeframe(event.target.value));
  };

  return (
    <Box sx={{ maxWidth: '100%' }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Market Analysis</Typography>
          <Typography variant="body2" color="text.secondary">Real-time technical analysis for {selectedInstrument}</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Instrument</InputLabel>
            <Select value={selectedInstrument} onChange={handleInstrumentChange} label="Instrument">
              <MenuItem value="NIFTY">NIFTY 50</MenuItem>
              <MenuItem value="SENSEX">SENSEX</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select value={selectedTimeframe} onChange={handleTimeframeChange} label="Timeframe">
              <MenuItem value="1m">1 Min</MenuItem>
              <MenuItem value="5m">5 Min</MenuItem>
              <MenuItem value="15m">15 Min</MenuItem>
            </Select>
          </FormControl>
          <Chip
            icon={<ShowChartIcon fontSize="small" />}
            label={isConnected ? 'Live' : 'Offline'}
            color={isConnected ? 'success' : 'error'}
            size="small"
            variant="outlined"
          />
        </Box>
      </Box>

      {/* Price Header */}
      <Box sx={{ mb: 3 }}>
        <Paper sx={{ p: 2, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'monospace' }}>
                ₹{currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {selectedInstrument} • {selectedTimeframe.toUpperCase()} • Last: {format(new Date(), 'HH:mm:ss')}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {Object.entries(indicators).map(([key, value]) => (
                <Box key={key} sx={{ position: 'relative' }}>
                  <Chip
                    label={`${key.toUpperCase()}: ${typeof value === 'number' ? value.toFixed(2) : value}`}
                    size="small"
                    variant="outlined"
                    color={getIndicatorColor(key, value, currentPrice)}
                  />
                </Box>
              ))}
            </Box>
          </Box>
        </Paper>
      </Box>

      {/* Main Chart + Side Panels */}
      <Grid container spacing={3}>
        {/* Chart */}
        <Grid item xs={12} lg={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="scrollable" sx={{ minWidth: 300 }}>
                  <Tab label="Price Chart" icon={<ShowChartIcon />} />
                  <Tab label="Indicators" icon={<TrendingUpIcon />} />
                </Tabs>
                <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={() => {}}>
                  Refresh
                </Button>
              </Box>
              
              {activeTab === 0 ? (
                <Box sx={{ height: 500 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={instrumentCandles.slice(-100)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis
                        dataKey="timestamp"
                        type="category"
                        stroke="#8b949e"
                        fontSize={11}
                        tick={{ fill: '#8b949e' }}
                        tickFormatter={(value) => format(new Date(value), 'HH:mm')}
                      />
                      <YAxis
                        stroke="#8b949e"
                        fontSize={11}
                        tick={{ fill: '#8b949e' }}
                        tickFormatter={val => `₹${val.toLocaleString()}`}
                      />
                      <Tooltip />
                      <Line type="monotone" dataKey="close" stroke="#8b949e" strokeWidth={1.5} dot={false} name="Close" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box sx={{ height: 500 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={instrumentCandles.slice(-100)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                      <XAxis dataKey="timestamp" type="category" stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} tickFormatter={(v) => format(new Date(v), 'HH:mm')} />
                      <YAxis stroke="#8b949e" fontSize={11} tick={{ fill: '#8b949e' }} tickFormatter={val => `₹${val.toLocaleString()}`} />
                      <Tooltip />
                      <Line type="monotone" dataKey="close" stroke="#8b949e" strokeWidth={1.5} dot={false} name="Close" />
                      {indicators.ema_9 && <Line type="monotone" dataKey="ema_9" stroke="#58a6ff" strokeWidth={1} dot={false} name="EMA 9" />}
                      {indicators.ema_20 && <Line type="monotone" dataKey="ema_20" stroke="#d29922" strokeWidth={1} dot={false} name="EMA 20" />}
                      {indicators.ema_50 && <Line type="monotone" dataKey="ema_50" stroke="#f85149" strokeWidth={1} dot={false} name="EMA 50" />}
                      {indicators.vwap && <Line type="monotone" dataKey="vwap" stroke="#00d4aa" strokeWidth={1.5} strokeDasharray="5 5" dot={false} name="VWAP" />}
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Side Panels */}
        <Grid item xs={12} lg={4}>
          {/* Market Regime */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Market Regime</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Chip
                  label={regime.regime?.replace('_', ' ')?.toUpperCase() || 'UNCERTAIN'}
                  size="medium"
                  color={getRegimeColor(regime.regime)}
                  variant="filled"
                />
                <Box>
                  <Typography variant="body2" color="text.secondary">Confidence</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 600, color: `${(regime.confidence || 0) > 0.7 ? 'success' : (regime.confidence || 0) > 0.4 ? 'warning' : 'error'}.main` }}>
                    {(regime.confidence * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <RegimeMetric label="ADX" value={regime.adx?.toFixed(1) || 'N/A'} />
                <RegimeMetric label="Trend" value={regime.trend_strength || 'N/A'} />
                <RegimeMetric label="Volatility" value={regime.volatility_state || 'N/A'} />
                <RegimeMetric label="EMA 9/20" value={regime.ema_9_20_state || 'N/A'} />
                <RegimeMetric label="EMA 20/50" value={regime.ema_20_50_state || 'N/A'} />
                <RegimeMetric label="VWAP State" value={regime.vwap_state || 'N/A'} />
                <RegimeMetric label="ATR %" value={regime.atr_pct?.toFixed(3) || 'N/A'} />
                <RegimeMetric label="Rel Volume" value={regime.relative_volume?.toFixed(2) || 'N/A'} />
              </Box>
            </CardContent>
          </Card>

          {/* Market Structure */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Market Structure</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <StructureItem label="Trend" value={structure.current_trend || 'sideways'} icon={<TrendingUpIcon />} />
                <StructureItem label="Breakout" value={structure.breakout_status?.replace('_', ' ') || 'none'} icon={<ExpandMoreIcon />} />
                <Divider />
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', mb: 1 }}>Key Levels</Typography>
                {structure.nearest_support && (
                  <LevelRow label="Support" value={structure.nearest_support} color="success" />
                )}
                {structure.nearest_resistance && (
                  <LevelRow label="Resistance" value={structure.nearest_resistance} color="error" />
                )}
                {structure.pdh && <LevelRow label="PDH" value={structure.pdh} color="info" />}
                {structure.pdl && <LevelRow label="PDL" value={structure.pdl} color="info" />}
              </Box>
            </CardContent>
          </Card>

          {/* Key Indicators */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Key Indicators</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {Object.entries(indicators).map(([key, value]) => (
                  <IndicatorRow key={key} label={key.toUpperCase()} value={typeof value === 'number' ? value.toFixed(2) : String(value)} />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

const RegimeMetric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{value}</Typography>
  </Box>
);

const StructureItem: React.FC<{ label: string; value: string; icon: React.ReactNode }> = ({ label, value, icon }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Box sx={{ p: 0.5, borderRadius: 1, bgcolor: 'action.hover' }}>{icon}</Box>
    <Typography variant="caption" color="text.secondary" sx={{ minWidth: 80 }}>{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, textTransform: 'capitalize' }}>{value}</Typography>
  </Box>
);

const LevelRow: React.FC<{ label: string; value: number; color: 'success' | 'error' | 'info' }> = ({ label, value, color }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', color: `${color}.main` }}>₹{value.toFixed(2)}</Typography>
  </Box>
);

const IndicatorRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{value}</Typography>
  </Box>
);

const getIndicatorColor = (key: string, value: any, price: number) => {
  if (typeof value !== 'number') return 'default';
  if (key.includes('ema') || key === 'vwap') {
    return value > price ? 'success' : 'error';
  }
  if (key === 'rsi') return value > 60 ? 'success' : value < 40 ? 'error' : 'warning';
  if (key === 'macd_histogram') return value > 0 ? 'success' : 'error';
  if (key === 'adx') return value > 25 ? 'success' : 'default';
  if (key === 'relative_volume') return value > 1.5 ? 'success' : 'default';
  return 'default';
};

const getRegimeColor = (regime?: string) => {
  const colors: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    strong_bullish: 'success',
    strong_bearish: 'error',
    breakout_transition: 'warning',
    high_volatility: 'warning',
    low_volatility: 'info',
    sideways: 'default',
    uncertain: 'default',
  };
  return colors[regime || ''] || 'default';
};

const generateMockIndicators = () => ({
  ema_9: 19850.25,
  ema_20: 19820.50,
  ema_50: 19750.75,
  vwap: 19830.00,
  rsi: 58.5,
  macd: 45.2,
  macd_signal: 42.1,
  macd_histogram: 3.1,
  adx: 28.5,
  plus_di: 22.3,
  minus_di: 18.7,
  atr: 145.3,
  atr_pct: 0.73,
  relative_volume: 1.35,
  bb_upper: 19980.50,
  bb_middle: 19820.50,
  bb_lower: 19660.50,
});

const generateMockStructure = () => ({
  current_trend: 'bullish',
  breakout_status: 'bullish_bos',
  nearest_support: 19750,
  nearest_resistance: 19950,
  pdh: 19920,
  pdl: 19680,
});

const generateMockRegime = () => ({
  regime: 'strong_bullish',
  confidence: 0.78,
  adx: 28.5,
  trend_strength: 'moderate',
  volatility_state: 'normal',
  ema_9_20_state: 'bullish',
  ema_20_50_state: 'bullish',
  vwap_state: 'above',
  atr_pct: 0.0073,
  relative_volume: 1.35,
});

export default MarketAnalysis;
