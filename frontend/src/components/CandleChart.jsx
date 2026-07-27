import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

const TOOLS = ['none', 'trendline', 'support_resistance'];

export default function CandleChart({
  data,
  signals,
  onTimeframeChange,
  onPauseToggle,
  onOrderSubmit,
  onCancelOrders,
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const prevDataLengthRef = useRef(0);
  const [tool, setTool] = useState('none');
  const [paused, setPaused] = useState(false);
  const drawingStartRef = useRef(null);

  const formatTime = useCallback((timeInput) => {
    const d = new Date(timeInput);
    const ms = d.getTime();
    if (!Number.isFinite(ms)) {
      return 0;
    }
    return Math.floor(ms / 1000);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#020617' },
        textColor: '#cbd5e1',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.08)',
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.08)',
        timeVisible: true,
        secondsVisible: false,
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    const series = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    const handler = (event) => {
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      )
        return;

      const key = event.key.toLowerCase();
      if (key === 'b') {
        event.preventDefault();
        onOrderSubmit?.({
          side: 'BUY',
          order_type: 'MARKET',
          quantity: suggestedQuantity(),
        });
      } else if (key === 's') {
        event.preventDefault();
        onOrderSubmit?.({
          side: 'SELL',
          order_type: 'MARKET',
          quantity: suggestedQuantity(),
        });
      } else if (key === 'escape') {
        event.preventDefault();
        onCancelOrders?.();
      } else if (key === ' ') {
        event.preventDefault();
        setPaused((prev) => {
          const next = !prev;
          onPauseToggle?.(next);
          return next;
        });
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onOrderSubmit, onCancelOrders, onPauseToggle]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || tool === 'none') return;

    const onMouseDown = (e) => {
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const price = chartRef.current?.priceScale('right')?.coordinateToPrice(y);
      const time = chartRef.current?.timeScale()?.coordinateToTime(x);
      drawingStartRef.current = { price: price || 0, time: time || 0 };
    };

    const onMouseUp = (e) => {
      if (!drawingStartRef.current) return;
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const endPrice = chartRef.current?.priceScale('right')?.coordinateToPrice(y);
      const endTime = chartRef.current?.timeScale()?.coordinateToTime(x);
      const start = drawingStartRef.current;

      if (tool === 'trendline' && endPrice && endTime) {
        chartRef.current?.createShape({
          points: [
            { time: start.time, price: start.price },
            { time: endTime, price: endPrice },
          ],
          shape: 'line',
          style: { stroke: '#facc15', width: 1.5, extendLeft: false, extendRight: false },
        });
      } else if (tool === 'support_resistance' && endPrice && endTime) {
        chartRef.current?.createShape({
          points: [
            { time: start.time, price: start.price },
            { time: endTime, price: endPrice },
          ],
          shape: 'rectangle',
          style: { fill: 'rgba(250,204,21,0.08)', stroke: '#facc15', width: 1 },
        });
      }
      drawingStartRef.current = null;
    };

    container.addEventListener('mousedown', onMouseDown);
    container.addEventListener('mouseup', onMouseUp);
    return () => {
      container.removeEventListener('mousedown', onMouseDown);
      container.removeEventListener('mouseup', onMouseUp);
    };
  }, [tool]);

  useEffect(() => {
    if (!seriesRef.current || !data || data.length === 0) return;
    const isAppend = !paused && data.length > prevDataLengthRef.current;

    const seen = new Set();
    const unique = [];
    for (const d of data) {
      const ts = formatTime(d.time);
      if (ts <= 0) continue;
      if (!seen.has(ts)) {
        seen.add(ts);
        unique.push(d);
      }
    }

    unique.sort((a, b) => formatTime(a.time) - formatTime(b.time));

    const formatted = unique.map((d) => {
      const ts = formatTime(d.time);
      return {
        time: ts,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      };
    });

    if (formatted.length === 1 || !isAppend) {
      seriesRef.current.setData(formatted);
    } else {
      seriesRef.current.update(formatted[formatted.length - 1]);
    }
    prevDataLengthRef.current = data.length;
  }, [data, paused, formatTime]);

  useEffect(() => {
    if (!chartRef.current || !signals) return;
    const maFast = signals.ma_fast;
    const maSlow = signals.ma_slow;
    if (maFast > 0 && maSlow > 0 && data && data.length > 0) {
      chartRef.current.applyOptions({
        priceScale: { autoScale: true },
      });
    }
  }, [signals, data]);

  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'];

  return (
    <>
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-slate-900/70 backdrop-blur-sm rounded-lg border border-slate-700 p-1">
        {timeframes.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange?.(tf)}
            className="text-[10px] font-mono px-1.5 py-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
          >
            {tf}
          </button>
        ))}
      </div>
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2 bg-slate-900/70 backdrop-blur-sm rounded-lg border border-slate-700 p-1">
        <button
          onClick={() => setTool('none')}
          className={`text-[10px] font-mono px-2 py-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors ${tool === 'none' ? 'bg-slate-700 text-white' : ''}`}
        >
          Cursor
        </button>
        <button
          onClick={() => setTool('trendline')}
          className={`text-[10px] font-mono px-2 py-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors ${tool === 'trendline' ? 'bg-slate-700 text-white' : ''}`}
        >
          Trendline
        </button>
        <button
          onClick={() => setTool('support_resistance')}
          className={`text-[10px] font-mono px-2 py-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors ${tool === 'support_resistance' ? 'bg-slate-700 text-white' : ''}`}
        >
          S/R Zone
        </button>
        <button
          onClick={() => setPaused((p) => !p)}
          className={`text-[10px] font-mono px-2 py-1 rounded hover:bg-slate-800 transition-colors ${paused ? 'bg-red-700 text-white' : 'text-slate-300 hover:text-white'}`}
        >
          {paused ? 'Resume' : 'Pause'}
        </button>
      </div>
      <div className="w-full h-full rounded-lg overflow-hidden border border-slate-700">
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </>
  );
}

function suggestedQuantity() {
  return 0.001;
}
