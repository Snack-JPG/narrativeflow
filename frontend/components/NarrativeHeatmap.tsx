'use client';

import { useState, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import { narrativeAPI } from '@/lib/api';
import { motion } from 'framer-motion';

interface HeatmapData {
  narrative: string;
  timeframe: string;
  value: number;
  sentiment: number;
  velocity: number;
}

interface Props {
  onNarrativeSelect: (narrative: string) => void;
}

const timeframes = ['1h', '4h', '24h', '7d', '30d'];
const narratives = ['AI', 'RWA', 'DePIN', 'Memecoin', 'L1/L2', 'NFT', 'DeFi', 'Gaming', 'Privacy', 'Social'];

export default function NarrativeHeatmap({ onNarrativeSelect }: Props) {
  const [data, setData] = useState<HeatmapData[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredCell, setHoveredCell] = useState<HeatmapData | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      // Fetch data for different timeframes
      const promises = timeframes.map(async (timeframe) => {
        const hours = timeframe === '1h' ? 1 : timeframe === '4h' ? 4 : timeframe === '24h' ? 24 : timeframe === '7d' ? 168 : 720;
        const stats = await narrativeAPI.getStats(hours);

        return narratives.map(narrative => ({
          narrative,
          timeframe,
          value: stats.narratives[narrative]?.social_mentions || 0,
          sentiment: stats.narratives[narrative]?.sentiment?.bullish || 0,
          velocity: Math.random() * 100, // Would be from velocity API
        }));
      });

      const results = await Promise.all(promises);
      setData(results.flat());
      setLoading(false);
    } catch (error) {
      console.error('Failed to load heatmap data:', error);
      setLoading(false);
    }
  };

  const colorScale = useMemo(() => {
    const maxValue = Math.max(...data.map(d => d.value));
    return d3.scaleSequential()
      .domain([0, maxValue])
      .interpolator(d3.interpolateViridis);
  }, [data]);

  const getHeatColor = (value: number, sentiment: number) => {
    // Blend momentum with sentiment
    const momentum = value / Math.max(...data.map(d => d.value));
    const hue = sentiment > 0 ? 120 : 0; // Green for bullish, red for bearish
    const saturation = Math.abs(sentiment) * 100;
    const lightness = 20 + (momentum * 40);
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="overflow-x-auto">
        <div className="min-w-[600px]">
          {/* Column Headers */}
          <div className="flex mb-2">
            <div className="w-24"></div>
            {timeframes.map(timeframe => (
              <div key={timeframe} className="flex-1 text-center text-sm text-gray-400">
                {timeframe}
              </div>
            ))}
          </div>

          {/* Heatmap Grid */}
          {narratives.map((narrative, i) => (
            <motion.div
              key={narrative}
              className="flex mb-1"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              {/* Row Header */}
              <div
                className="w-24 text-sm text-gray-300 flex items-center cursor-pointer hover:text-primary-400"
                onClick={() => onNarrativeSelect(narrative)}
              >
                {narrative}
              </div>

              {/* Cells */}
              {timeframes.map(timeframe => {
                const cellData = data.find(d => d.narrative === narrative && d.timeframe === timeframe);
                if (!cellData) return <div key={timeframe} className="flex-1" />;

                return (
                  <div
                    key={timeframe}
                    className="flex-1 p-1"
                    onMouseEnter={() => setHoveredCell(cellData)}
                    onMouseLeave={() => setHoveredCell(null)}
                  >
                    <motion.div
                      className="h-12 rounded cursor-pointer heatmap-cell relative overflow-hidden"
                      style={{
                        background: getHeatColor(cellData.value, cellData.sentiment),
                        border: hoveredCell === cellData ? '2px solid #1677ff' : '1px solid rgba(255,255,255,0.1)'
                      }}
                      whileHover={{ scale: 1.05 }}
                      onClick={() => onNarrativeSelect(narrative)}
                    >
                      {/* Velocity indicator */}
                      {cellData.velocity > 70 && (
                        <div className="absolute top-1 right-1 w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                      )}

                      {/* Value display */}
                      <div className="flex items-center justify-center h-full text-xs text-white/80">
                        {cellData.value > 1000 ? `${(cellData.value / 1000).toFixed(1)}k` : cellData.value}
                      </div>
                    </motion.div>
                  </div>
                );
              })}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {hoveredCell && (
        <div className="absolute z-10 glass rounded-lg p-3 text-sm"
          style={{
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '10px'
          }}>
          <div className="font-semibold text-primary-400">{hoveredCell.narrative}</div>
          <div className="text-gray-300">Period: {hoveredCell.timeframe}</div>
          <div className="text-gray-300">Mentions: {hoveredCell.value}</div>
          <div className="text-gray-300">
            Sentiment: {hoveredCell.sentiment > 0 ? '🟢' : '🔴'} {Math.abs(hoveredCell.sentiment).toFixed(0)}%
          </div>
          <div className="text-gray-300">Velocity: {hoveredCell.velocity.toFixed(0)}/hr</div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded bg-red-500"></div>
            <span>Bearish</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded bg-gray-500"></div>
            <span>Neutral</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded bg-green-500"></div>
            <span>Bullish</span>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
          <span>High Velocity</span>
        </div>
      </div>
    </div>
  );
}