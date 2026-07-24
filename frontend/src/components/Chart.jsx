import { useEffect, useRef, useCallback, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

export default function Chart({ data, signals }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#cbd5e1',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;
    setChartReady(true);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
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
    if (!chartReady || !seriesRef.current || !data || data.length === 0) return;
    const formatted = data.map(d => ({
      time: new Date(d.time).toISOString().split('T')[0],
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    seriesRef.current.setData(formatted);
  }, [chartReady, data]);

  useEffect(() => {
    if (!chartRef.current || !signals) return;
    const maFast = signals.ma_fast;
    const maSlow = signals.ma_slow;
    if (maFast > 0 && maSlow > 0 && data && data.length > 0) {
      chartRef.current.applyOptions({
        priceScale: {
          autoScale: true,
        },
      });
    }
  }, [signals, data]);

  return (
    <div className="w-full h-full rounded-lg overflow-hidden border border-slate-700">
      <div ref={chartContainerRef} className="w-full h-full" />
      {signals && (
        <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur-sm rounded-lg p-3 border border-slate-700 text-xs space-y-1">
          <div className="text-slate-400">Signal: <span className={`font-bold ${signals.signal === 'BUY' ? 'text-green-400' : signals.signal === 'SELL' ? 'text-red-400' : 'text-slate-300'}`}>{signals.signal}</span></div>
          <div className="text-slate-400">EMA Fast: <span className="text-slate-200">{signals.ma_fast.toFixed(2)}</span></div>
          <div className="text-slate-400">EMA Slow: <span className="text-slate-200">{signals.ma_slow.toFixed(2)}</span></div>
          <div className="text-slate-400">RSI: <span className="text-slate-200">{signals.rsi.toFixed(2)}</span></div>
        </div>
      )}
    </div>
  );
}
