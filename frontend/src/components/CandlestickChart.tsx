import React, { useMemo, useState } from 'react';

interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface CandlestickChartProps {
  data: Candle[];
  height?: number;
  showTooltip?: boolean;
}

/**
 * Pure SVG candlestick chart (no extra dependency).
 * Each candle: vertical wick (low->high) + body rect (open->close).
 * Green = close >= open, Red = close < open.
 */
const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  height = 420,
  showTooltip = true,
}) => {
  const [hover, setHover] = useState<{ index: number; price: number } | null>(null);

  const display = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.slice(-120);
  }, [data]);

  const n = display.length;

  const xLabels = useMemo(
    () =>
      display.map((_, i) => {
        if (n <= 12) return i;
        const step = Math.ceil(n / 12);
        return i % step === 0 ? i : -1;
      }),
    [n, display]
  );

  if (display.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#8b949e',
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 13,
        }}
      >
        No candle data
      </div>
    );
  }

  const prices = display.flatMap((d) => [d.high, d.low]);
  const priceMin = Math.min(...prices);
  const priceMax = Math.max(...prices);
  const priceRange = priceMax - priceMin || 1;

  const padTop = 30;
  const padBottom = 26;
  const padLeft = 6;
  const padRight = 6;
  const innerH = height - padTop - padBottom;

  const yForPrice = (p: number) => {
    const frac = (priceMax - p) / priceRange;
    return padTop + frac * innerH;
  };

  const candleWidth = Math.max(6, Math.min(16, (100 - padLeft - padRight) / n));
  const gap = Math.max(2, Math.min(6, (100 - padLeft - padRight) / n / 2));

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return ts;
    }
  };

  return (
    <div
      style={{
        width: '100%',
        height,
        position: 'relative',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        background: '#0d1117',
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      {/* Y axis labels */}
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 32, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', paddingTop: padTop, paddingBottom: padBottom, pointerEvents: 'none' }}>
        {[priceMax, (priceMax + priceMin) / 2, priceMin].map((p, i) => (
          <div
            key={i}
            style={{
              fontSize: 10,
              color: '#8b949e',
              textAlign: 'right',
              width: 28,
              position: 'absolute',
              top: `${((priceMax - p) / priceRange) * 100}%`,
              transform: 'translateY(-50%)',
              marginRight: 4,
            }}
          >
            {p.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        ))}
      </div>

      {/* X axis labels */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: padBottom, display: 'flex', paddingLeft: padLeft, paddingRight: padRight, pointerEvents: 'none' }}>
        {xLabels.map((idx) => {
          if (idx === -1 || idx >= n) return null;
          const w = (100 - padLeft - padRight) / n;
          return (
            <div
              key={idx}
              style={{
                fontSize: 10,
                color: '#8b949e',
                position: 'absolute',
                left: `${padLeft + idx * w}%`,
                transform: 'translateX(-50%)',
                bottom: 4,
                whiteSpace: 'nowrap',
              }}
            >
              {formatTime(display[idx].timestamp)}
            </div>
          );
        })}
      </div>

      {/* Chart area */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          padding: `${padTop}px ${padRight}px ${padBottom}px ${padLeft}px`,
        }}
      >
        {/* Grid lines */}
        {[priceMax, (priceMax + priceMin) / 2, priceMin].map((p, i) => (
          <div
            key={`grid-${i}`}
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: `${((priceMax - p) / priceRange) * 100}%`,
              height: 1,
              background: '#30363d',
              transform: 'translateY(-50%)',
              pointerEvents: 'none',
              zIndex: 0,
            }}
          />
        ))}

        {/* Candles */}
        {display.map((candle, i) => {
          const isUp = candle.close >= candle.open;
          const top = Math.min(yForPrice(candle.open), yForPrice(candle.close));
          const bottom = Math.max(yForPrice(candle.open), yForPrice(candle.close));
          const bodyH = Math.max(1, bottom - top);
          const wickTop = yForPrice(candle.high);
          const wickBottom = yForPrice(candle.low);
          const x = padLeft + i * ((100 - padLeft - padRight) / n) + gap / 2;

          const onEnter = () => setHover({ index: i, price: candle.close });
          const onLeave = () => setHover(null);

          const bodyColor = isUp ? '#00d4aa' : '#f85149';
          const wickColor = isUp ? '#00d4aa' : '#f85149';

          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: 0,
                bottom: 0,
                width: candleWidth,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'pointer',
              }}
              onMouseEnter={onEnter}
              onMouseLeave={onLeave}
            >
              {/* Wick */}
              <div
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: `${(wickTop / height) * 100}%`,
                  height: Math.max(1, ((wickBottom - wickTop) / height) * 100),
                  width: 1.5,
                  background: wickColor,
                  transform: 'translateX(-50%)',
                  zIndex: 1,
                  pointerEvents: 'none',
                }}
              />
              {/* Body */}
              <div
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: `${(top / height) * 100}%`,
                  height: `${(bodyH / height) * 100}%`,
                  width: `${candleWidth * 0.85}%`,
                  background: bodyColor,
                  transform: 'translateX(-50%)',
                  zIndex: 2,
                  borderRadius: 1,
                  opacity: hover ? (hover.index === i ? 1 : 0.35) : 1,
                  transition: 'opacity 0.1s',
                }}
              />
            </div>
          );
        })}

        {/* Hover tooltip line */}
        {hover && showTooltip && (
          <div
            style={{
              position: 'absolute',
              left: `${padLeft + hover.index * ((100 - padLeft - padRight) / n)}%`,
              top: 0,
              bottom: 0,
              width: 1,
              background: '#58a6ff',
              zIndex: 3,
              pointerEvents: 'none',
              transform: 'translateX(-50%)',
            }}
          />
        )}
      </div>

      {/* Floating tooltip box */}
      {hover && showTooltip && (
        <div
          style={{
            position: 'absolute',
            left: `${padLeft + hover.index * ((100 - padLeft - padRight) / n)}%`,
            top: `${padTop}px`,
            transform: 'translateX(-50%)',
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: 4,
            padding: '6px 10px',
            fontSize: 12,
            color: '#c9d1d9',
            zIndex: 10,
            pointerEvents: 'none',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            whiteSpace: 'nowrap',
          }}
        >
          <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 2 }}>
            {formatTime(display[hover.index].timestamp)}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span style={{ color: '#8b949e' }}>O</span>
            <span>{display[hover.index].open.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span style={{ color: '#8b949e' }}>H</span>
            <span>{display[hover.index].high.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span style={{ color: '#8b949e' }}>L</span>
            <span>{display[hover.index].low.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>C</span>
            <span style={{ color: display[hover.index].close >= display[hover.index].open ? '#00d4aa' : '#f85149', fontWeight: 600 }}>
              {display[hover.index].close.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandlestickChart;
