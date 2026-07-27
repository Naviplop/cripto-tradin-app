import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';

type Tool = 'none' | 'trendline' | 'fibonacci' | 'support_resistance';

export default function CandleChart({
  data,
  signals,
  onTimeframeChange,
  onPauseToggle,
  onOrderSubmit,
  onCancelOrders,
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const prevDataLengthRef = useRef(0);
  const [tool, setTool] = useState<Tool>('none');
  const [paused, setPaused] = useState(false);
  const [drawnItems, setDrawnItems] = useState([]);
  const drawingStartRef = useRef<{ price: number; time: Time } | null>(null);

  const formatTime = useCallback((timeInput: string | number | Date) => {
    const d = new Date(timeInput);
    return {
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      day: d.getDate(),
      hour: d.getHours(),
      minute: d.getMinutes(),
    };
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

  // Hotkeys
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
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
        setPaused(prev => {
          const next = !prev;
          onPauseToggle?.(next);
          return next;
        });
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onOrderSubmit, onCancelOrders, onPauseToggle]);

  // Drawing tools
  useEffect(() => {
    const container = containerRef.current;
    if (!container || tool === 'none') return;

    const onMouseDown = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const price = chartRef.current?.priceScale('right')?.coordinateToPrice(y);
      const time = chartRef.current?.timeScale()?.coordinateToTime(x);
      drawingStartRef.current = { price: price || 0, time: time || 0 };
    };

    const onMouseUp = (e: MouseEvent) => {
      if (!drawingStartRef.current) return;
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const endPrice = chartRef.current?.priceScale('right')?.coordinateToPrice(y);
      const endTime = chartRef.current?.timeScale()?.coordinateToTime(x);
      const start = drawingStartRef.current;

      setDrawnItems(prev => {
        const next = [...prev];
        if (tool === 'trendline' && endPrice && endTime) {
          next.push({
            type: 'line',
            start: { price: start.price, time: start.time },
            end: { price: endPrice, time: endTime },
          });
        } else if (
          tool === 'support_resistance'
          && endPrice
          && endTime
        ) {
          next.push({
            type: 'rect',
            start: { price: start.price, time: start.time },
            end: { price: endPrice, time: endTime },
          });
        }
        return next;
      });
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
    const formatted: CandlestickData[] = data.map(d => ({
      time: formatTime(d.time) as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    if (isAppend && formatted.length > 0) {
      seriesRef.current.update(formatted[formatted.length - 1]);
    } else {
      seriesRef.current.setData(formatted);
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

  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'] as const;

  return (
    <>
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-slate-900/70 backdrop-blur-sm rounded-lg border border-slate-700 p-1">
        {timeframes.map(tf => (
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
          onClick={() => setPaused(p => !p)}
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

function suggestedQuantity(): number {
  return 0.001;
}
