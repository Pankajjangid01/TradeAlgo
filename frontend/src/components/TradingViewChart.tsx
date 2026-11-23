import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, CandlestickSeries, CandlestickSeriesOptions } from 'lightweight-charts';

interface TradingViewChartProps {
  symbol?: string;
  data?: any[];
  currentPrice?: number;
}

const parseTime = (d: any): number => {
  const rawTime = d?.timestamp ?? d?.time ?? d?.Date ?? 0;
  try {
    if (typeof rawTime === 'number') {
      return rawTime > 10000000000 ? Math.floor(rawTime / 1000) : rawTime;
    }
    const ts = new Date(rawTime).getTime();
    return isNaN(ts) ? Math.floor(Date.now() / 1000) : Math.floor(ts / 1000);
  } catch {
    return Math.floor(Date.now() / 1000);
  }
};

const parseNum = (v: any, fallback = 0): number => {
  const n = Number(v);
  return isNaN(n) ? fallback : n;
};

const TradingViewChart: React.FC<TradingViewChartProps> = ({ symbol = 'NIFTY', data = [], currentPrice = 0 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d1117' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#1e222d' },
        horzLines: { color: '#1e222d' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      width: containerRef.current.clientWidth || 600,
      height: containerRef.current.clientHeight || 440,
      rightPriceScale: {
        visible: true,
        borderColor: '#2a2e39',
        autoScale: true,
      },
      leftPriceScale: {
        visible: true,
        borderColor: '#2a2e39',
        autoScale: true,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candlestickSeriesInstance = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    } as CandlestickSeriesOptions);

    chartRef.current = chart;
    seriesRef.current = candlestickSeriesInstance;

    const validData = (data || []).filter((d: any) => d != null);
    const formattedData = validData.map((d: any) => ({
      time: parseTime(d),
      open: parseNum(d.open),
      high: parseNum(d.high),
      low: parseNum(d.low),
      close: parseNum(d.close),
    }));

    try {
      candlestickSeriesInstance.setData(formattedData as any);
    } catch (e) {
      console.error('Error setting chart data:', e);
    }

    const handleResize = () => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight || 440,
      });
    };

    window.addEventListener('resize', handleResize);

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0] && chartRef.current) {
        const { width, height } = entries[0].contentRect;
        chartRef.current.applyOptions({ width, height: height || 440 });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      try {
        chart.remove();
      } catch { /* Lightweight Charts may already be disposed during React dev remounts */ }
      if (chartRef.current === chart) chartRef.current = null;
      if (seriesRef.current === candlestickSeriesInstance) seriesRef.current = null;
    };
  }, []);

  // Update last candle with live price without recreating the chart
  useEffect(() => {
    if (!seriesRef.current || !data || data.length === 0 || currentPrice <= 0) return;

    try {
      const last = data[data.length - 1];
      if (!last) return;
      const updated = [...data];
      updated[updated.length - 1] = {
        ...last,
        close: currentPrice,
        high: Math.max(parseNum(last.high, last.close), currentPrice),
        low: Math.min(parseNum(last.low, last.close), currentPrice),
      };
      seriesRef.current.setData(updated.map((d: any) => ({
        time: parseTime(d),
        open: parseNum(d.open),
        high: parseNum(d.high),
        low: parseNum(d.low),
        close: parseNum(d.close),
      })) as any);
    } catch (e) {
      console.error('Error updating chart price:', e);
    }
  }, [data, currentPrice, seriesRef.current]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', minHeight: 440, backgroundColor: '#0d1117' }}
    />
  );
};

export default TradingViewChart;
