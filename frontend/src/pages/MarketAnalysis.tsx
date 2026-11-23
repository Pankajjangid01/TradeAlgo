import React, { useEffect, useState, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store/index';
import {
  setLoadingState,
  addNotification,
} from '../store/uiSlice';
import {
  setSelectedInstrument,
  setSelectedTimeframe,
  setCandles,
  setTicks,
} from '../store/marketSlice';
import { api } from '../services/api';
import { wsService } from '../services/websocket';
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
  Alert,
  Tabs,
  Tab,
  Skeleton,
  Paper,
  Button,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  ShowChart as ShowChartIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import TradingViewChart from '../components/TradingViewChart';

const MarketAnalysis: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const {
    selectedInstrument: rawInstrument,
    selectedTimeframe: rawTimeframe,
    candles,
    ticks,
    isConnected,
    lastUpdate,
  } = useSelector((state: RootState) => state.market);
  const selectedInstrument = rawInstrument || 'NIFTY';
  const selectedTimeframe = rawTimeframe || '5m';
  const signals = useSelector((state: RootState) => state.signals.signals);
  const [activeTab, setActiveTab] = useState(0);
  const [indicators, setIndicators] = useState<any>({});
  const [structure, setStructure] = useState<any>({});
  const [regime, setRegime] = useState<any>({});

  const [lastKnownPrice, setLastKnownPrice] = useState<number>(0);

  const instrumentCandles =
    candles[`${selectedInstrument}_${selectedTimeframe}`] || [];
  const latestTick = ticks[selectedInstrument];
  const livePrice =
    latestTick?.ltp ??
    (instrumentCandles.length > 0
      ? instrumentCandles[instrumentCandles.length - 1].close
      : 0) ??
    lastKnownPrice ??
    0;

  useEffect(() => {
    // Persist last known price when we receive a live tick
    if (livePrice > 0) {
      setLastKnownPrice(livePrice);
    }
  }, [livePrice]);

  const currentPrice = livePrice > 0 ? livePrice : lastKnownPrice;

  // Track subscribed tokens to prevent duplicate WebSocket subscribe calls
  const subscribedTokensRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    dispatch(setLoadingState({ key: 'market-analysis', loading: true }));

    // Connect websocket if not already
    wsService.connect();

    // Connection status listener
    const unsubscribeConnection = wsService.onConnectionChange((connected) => {
      dispatch({
        type: 'market/setConnectionStatus',
        payload: {
          connected,
          error: connected ? undefined : 'Disconnected from market data',
        },
      });
    });

    // Subscribe to live candles for selected instrument
    const unsubscribeCandle = wsService.onMarketData(
      'candle',
      (data: any) => {
        if (!data) return;
        const candle = {
          instrument_token: data.instrument_token || data.symbol || selectedInstrument,
          timeframe: data.timeframe || selectedTimeframe,
          timestamp: data.timestamp || new Date().toISOString(),
          open: data.open ?? data.o,
          high: data.high ?? data.h,
          low: data.low ?? data.l,
          close: data.close ?? data.c,
          volume: data.volume ?? data.v,
        };
        const key = `${candle.instrument_token}_${candle.timeframe}`;
        const existing = candles[key] || [];
        const next = [...existing, candle].slice(-500);
        dispatch(setCandles({ instrument: candle.instrument_token, timeframe: candle.timeframe, candles: next }));
      }
    );

    // Subscribe to live ticks
    const unsubscribeTick = wsService.onMarketData(
      'tick',
      (data: any) => {
        if (!data || !Array.isArray(data) || data.length === 0) return;
        // Map incoming ticks to selectedInstrument key so ticks[selectedInstrument] lookup works
        const normalized = data.map((tick: any) => ({
          ...tick,
          instrument_token: selectedInstrument,
        }));
        dispatch(setTicks(normalized));
      }
    );

    // Subscribe to instrument tokens - only when token set changes
    const currentTokens = new Set([selectedInstrument]);
    const prevTokens = subscribedTokensRef.current;
    const toUnsubscribe = Array.from(prevTokens).filter(t => !currentTokens.has(t));
    const toSubscribe = Array.from(currentTokens).filter(t => !prevTokens.has(t));
    if (toUnsubscribe.length > 0) {
      wsService.unsubscribe(toUnsubscribe);
    }
    if (toSubscribe.length > 0) {
      wsService.subscribe(toSubscribe);
    }
    subscribedTokensRef.current = currentTokens;

    // Load initial historical candles from REST API
    const loadHistory = async () => {
      try {
        const from = new Date();
        from.setDate(from.getDate() - 1);
        const to = new Date();
        const res = await api.getHistorical(
          selectedInstrument,
          selectedTimeframe,
          from.toISOString(),
          to.toISOString(),
          "NSE"
        );
        const hist = res.data?.data || [];
        if (hist.length > 0) {
          const key = `${selectedInstrument}_${selectedTimeframe}`;
          const normalized = hist.map((c: any) => ({
            instrument_token: selectedInstrument,
            timeframe: selectedTimeframe,
            timestamp: c.timestamp || c.t || c.time,
            open: c.open ?? c.o,
            high: c.high ?? c.h,
            low: c.low ?? c.l,
            close: c.close ?? c.c,
            volume: c.volume ?? c.v,
          }));
          dispatch(setCandles({ instrument: selectedInstrument, timeframe: selectedTimeframe, candles: normalized }));
        }
      } catch (error) {
        console.error("Failed to load historical candles:", error);
      }
    };
    loadHistory();

    // Fetch live LTP via REST API
    const fetchLTP = async () => {
      try {
        const res = await api.getLTP(selectedInstrument, "NSE");
        const ltpData = res.data?.data;
        let ltp: number | null = null;
        if (ltpData) {
          // Angel One nested format: {"status": true, "data": {"fetched": [{"ltp": ...}]}}
          if (ltpData.data && Array.isArray(ltpData.data.fetched) && ltpData.data.fetched.length > 0) {
            ltp = ltpData.data.fetched[0].ltp;
          }
          // Angel One flat format: {"data": {"fetched": [{"ltp": ...}]}}
          else if (Array.isArray(ltpData.fetched) && ltpData.fetched.length > 0) {
            ltp = ltpData.fetched[0].ltp;
          }
          // Yahoo/symbol-keyed format: {"NIFTY": {"ltp": ...}}
          else if (ltpData[selectedInstrument]) {
            ltp = ltpData[selectedInstrument].ltp;
          }
          // Flat dict format
          else if (typeof ltpData === 'object' && 'ltp' in ltpData) {
            ltp = ltpData.ltp;
          }
        }
        if (ltp) {
          dispatch(setTicks([{ instrument_token: selectedInstrument, ltp, timestamp: new Date().toISOString(), volume: 0 }]));
        }
      } catch (error) {
        console.error("Failed to fetch LTP:", error);
      }
    };

    // Fetch LTP immediately and then poll every 5 seconds
    fetchLTP();
    const ltpInterval = setInterval(fetchLTP, 5000);

    // Load initial indicators/structure/regime (mock fallback until backend provides live)
    const loadStatic = async () => {
      try {
        await new Promise((resolve) => setTimeout(resolve, 300));
        setIndicators(generateMockIndicators(currentPrice));
        setStructure(generateMockStructure(currentPrice));
        setRegime(generateMockRegime(currentPrice));
      } catch (error) {
        console.error('Failed to load market analysis:', error);
      } finally {
        dispatch(setLoadingState({ key: 'market-analysis', loading: false }));
      }
    };
    loadStatic();

    return () => {
      unsubscribeConnection();
      unsubscribeCandle();
      unsubscribeTick();
      wsService.unsubscribe(Array.from(currentTokens));
      clearInterval(ltpInterval);
    };
  }, [dispatch, selectedInstrument, selectedTimeframe, wsService]);

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
          <Typography variant="body2" color="text.secondary">Live technical analysis for {selectedInstrument}</Typography>
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
                {selectedInstrument} • {selectedTimeframe.toUpperCase()} • Last: {format(new Date(latestTick?.timestamp || lastUpdate || new Date().toISOString()), 'HH:mm:ss')}
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
                  <Tab label="Candlestick Chart" icon={<ShowChartIcon />} />
                  <Tab label="Indicators" icon={<TrendingUpIcon />} />
                </Tabs>
                <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={() => {}}>
                  Refresh
                </Button>
              </Box>

                  {activeTab === 0 ? (
                    <Box sx={{ height: 500, width: '100%' }}>
                      <TradingViewChart symbol={selectedInstrument} data={instrumentCandles} currentPrice={currentPrice} />
                    </Box>
                  ) : (
                <Box sx={{ height: 500, width: '100%' }}>
                  <ResponsiveContainerShim data={instrumentCandles} indicators={indicators} currentPrice={currentPrice} />
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

// Fallback indicators tab (keeps recharts line for indicators view)
const ResponsiveContainerShim: React.FC<{ data: any[]; indicators: any; currentPrice: number }> = ({ data, indicators, currentPrice }) => (
  <Box sx={{ height: 440, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e' }}>
    Switch to Candlestick Chart tab for live OHLC view.
  </Box>
);

const RegimeMetric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
    <Typography variant="caption" color="text.secondary">{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{value}</Typography>
  </Box>
);

const StructureItem: React.FC<{ label: string; value: string; icon: React.ReactNode }> = ({ label, value, icon }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, borderRadius: 1, bgcolor: 'action.hover' }}>
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

const generateMockIndicators = (price: number) => ({
  ema_9: price * 0.998,
  ema_20: price * 0.995,
  ema_50: price * 0.99,
  vwap: price * 0.997,
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
  bb_upper: price * 1.008,
  bb_middle: price,
  bb_lower: price * 0.992,
});

const generateMockStructure = (price: number) => ({
  current_trend: 'bullish',
  breakout_status: 'bullish_bos',
  nearest_support: price * 0.985,
  nearest_resistance: price * 1.015,
  pdh: price * 1.01,
  pdl: price * 0.99,
});

const generateMockRegime = (price: number) => ({
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
