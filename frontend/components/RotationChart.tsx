'use client';

import { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import { divergenceAPI } from '@/lib/api';
import { motion } from 'framer-motion';

interface RotationData {
  time: Time;
  AI: number;
  RWA: number;
  DePIN: number;
  Memecoin: number;
  DeFi: number;
}

export default function RotationChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRefs = useRef<Map<string, ISeriesApi<'Area'>>>(new Map());
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [loading, setLoading] = useState(true);

  const narrativeColors = {
    AI: '#1677ff',
    RWA: '#52c41a',
    DePIN: '#faad14',
    Memecoin: '#f5222d',
    DeFi: '#722ed1'
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: 'rgba(255, 255, 255, 0.1)',
          style: 2,
        },
        horzLine: {
          width: 1,
          color: 'rgba(255, 255, 255, 0.1)',
          style: 2,
        },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
    });

    chartRef.current = chart;

    // Create area series for each narrative
    Object.entries(narrativeColors).forEach(([narrative, color]) => {
      const series = chart.addAreaSeries({
        lineColor: color,
        topColor: color + '40',
        bottomColor: color + '10',
        lineWidth: 2,
        title: narrative,
        priceFormat: {
          type: 'percent',
        },
      });
      seriesRefs.current.set(narrative, series);
    });

    // Load data
    loadHistoricalData();

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
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
    loadHistoricalData();
  }, [selectedPeriod]);

  const loadHistoricalData = async () => {
    try {
      const days = selectedPeriod === '7d' ? 7 : selectedPeriod === '30d' ? 30 : 90;

      // Generate mock historical data
      const data = generateMockData(days);

      // Update each series
      seriesRefs.current.forEach((series, narrative) => {
        const seriesData = data.map(d => ({
          time: d.time,
          value: (d as any)[narrative] || 0
        }));
        series.setData(seriesData);
      });

      if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
      }

      setLoading(false);
    } catch (error) {
      console.error('Failed to load rotation data:', error);
      setLoading(false);
    }
  };

  const generateMockData = (days: number): RotationData[] => {
    const data: RotationData[] = [];
    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;

    // Simulate capital rotation patterns
    for (let i = days; i >= 0; i--) {
      const date = new Date(now - i * dayMs);
      const dayOfCycle = (days - i) % 30;

      // Create rotation pattern
      const aiPhase = Math.sin((dayOfCycle / 30) * Math.PI * 2) * 20 + 30;
      const rwaPhase = Math.sin((dayOfCycle / 30) * Math.PI * 2 + Math.PI / 3) * 15 + 20;
      const depinPhase = Math.sin((dayOfCycle / 30) * Math.PI * 2 + (Math.PI * 2) / 3) * 10 + 15;
      const memePhase = Math.sin((dayOfCycle / 30) * Math.PI * 2 + Math.PI) * 25 + 25;
      const defiPhase = Math.sin((dayOfCycle / 30) * Math.PI * 2 + Math.PI / 2) * 12 + 10;

      data.push({
        time: (date.getTime() / 1000) as Time,
        AI: Math.max(0, aiPhase + Math.random() * 5),
        RWA: Math.max(0, rwaPhase + Math.random() * 3),
        DePIN: Math.max(0, depinPhase + Math.random() * 2),
        Memecoin: Math.max(0, memePhase + Math.random() * 8),
        DeFi: Math.max(0, defiPhase + Math.random() * 3),
      });
    }

    return data;
  };

  return (
    <div className="space-y-4">
      {/* Period Selector */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-400">Capital Flow Distribution</h3>
        <div className="flex space-x-2">
          {(['7d', '30d', '90d'] as const).map(period => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                selectedPeriod === period
                  ? 'bg-primary-600 text-white'
                  : 'bg-dark-400 text-gray-400 hover:bg-dark-500'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-dark-100/50 z-10">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-[300px]" />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-4 text-xs">
        {Object.entries(narrativeColors).map(([narrative, color]) => (
          <div key={narrative} className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: color }}></div>
            <span className="text-gray-400">{narrative}</span>
          </div>
        ))}
      </div>

      {/* Insights */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-lg p-4"
      >
        <h4 className="text-xs font-semibold text-gray-400 mb-2">Rotation Insights</h4>
        <div className="space-y-2 text-xs text-gray-300">
          <div className="flex items-center justify-between">
            <span>Current Leader:</span>
            <span className="font-semibold text-primary-400">AI Narrative (35%)</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Gaining Momentum:</span>
            <span className="text-green-400">RWA (+12% this week)</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Losing Steam:</span>
            <span className="text-red-400">Memecoins (-18% this week)</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Next Rotation:</span>
            <span className="text-yellow-400">DePIN (early signals)</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}