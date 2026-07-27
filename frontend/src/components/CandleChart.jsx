import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

export default function CandleChart({ data, signals }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const prevDataLengthRef = useRef(0);

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
      crosshair: {
        mode: 1,
      },
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
    if (!seriesRef.current || !data || data.length === 0) return;
    const isAppend = data.length > prevDataLengthRef.current;
    const formatted = data.map(d => ({
      time: {
        year: new Date(d.time).getFullYear(),
        month: new Date(d.time).getMonth() + 1,
        day: new Date(d.time).getDate(),
        hour: new Date(d.time).getHours(),
        minute: new Date(d.time).getMinutes(),
      },
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
  }, [data]);

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

  return (
    <div className="w-full h-full rounded-lg overflow-hidden border border-slate-700">
      <div ref={containerRef} className="w-full h-full" />
      {signals && (
        <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur-sm rounded-lg p-3 border border-slate-700 text-xs space-y-1">
          <div className="text-slate-400">Signal: <span className={`font-bold ${signals.signal === 'BUY' ? 'text-emerald-400' : signals.signal === 'SELL' ? 'text-red-400' : 'text-slate-300'}`}>{signals.signal}</span></div>
          <div className="text-slate-400">EMA Fast: <span className="text-slate-200">{signals.ma_fast.toFixed(2)}</span></div>
          <div className="text-slate-400">EMA Slow: <span className="text-slate-200">{signals.ma_slow.toFixed(2)}</span></div>
          <div className="text-slate-400">RSI: <span className="text-slate-200">{signals.rsi.toFixed(2)}</span></div>
          {signals.ai_probability > 0 && (
            <div className="text-slate-400">AI Prob: <span className="text-cyan-300">{signals.ai_probability.toFixed(2)}</span></div>
          )}
        </div>
      )}
    </div>
  );
}
