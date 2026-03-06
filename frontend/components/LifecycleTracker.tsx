'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { narrativeAPI, LifecycleData } from '@/lib/api';

interface Props {
  selectedNarrative: string | null;
}

const lifecycleStages = [
  { key: 'whisper', label: 'Whisper', color: 'bg-purple-600', description: 'Early signals, alpha groups' },
  { key: 'emerging', label: 'Emerging', color: 'bg-blue-600', description: 'Growing momentum' },
  { key: 'mainstream', label: 'Mainstream', color: 'bg-green-600', description: 'Widespread adoption' },
  { key: 'peak', label: 'Peak FOMO', color: 'bg-yellow-600', description: 'Maximum hype' },
  { key: 'declining', label: 'Declining', color: 'bg-orange-600', description: 'Losing steam' },
  { key: 'dead', label: 'Dead', color: 'bg-red-600', description: 'No activity' },
];

export default function LifecycleTracker({ selectedNarrative }: Props) {
  const [data, setData] = useState<LifecycleData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const lifecycleData = await narrativeAPI.getLifecycle();
      setData(lifecycleData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load lifecycle data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!data) {
    return <div className="text-center text-gray-500">No lifecycle data available</div>;
  }

  return (
    <div className="space-y-6">
      {/* Visual Pipeline */}
      <div className="relative">
        <div className="flex items-center justify-between">
          {lifecycleStages.map((stage, index) => (
            <div key={stage.key} className="flex-1 relative">
              {/* Connection line */}
              {index < lifecycleStages.length - 1 && (
                <div className="absolute top-6 left-1/2 w-full h-0.5 bg-dark-400 z-0"></div>
              )}

              {/* Stage circle */}
              <div className="relative z-10 flex flex-col items-center">
                <motion.div
                  className={`w-12 h-12 rounded-full ${stage.color} flex items-center justify-center text-white font-bold shadow-lg`}
                  whileHover={{ scale: 1.1 }}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  {data.summary[stage.key] || 0}
                </motion.div>
                <div className="mt-2 text-xs text-gray-400 text-center">
                  <div className="font-semibold">{stage.label}</div>
                  <div className="text-[10px]">{stage.description}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Narrative Cards by Stage */}
      <div className="grid grid-cols-3 gap-4">
        {lifecycleStages.slice(0, 3).map(stage => {
          const narratives = data.lifecycle_stages[stage.key as keyof typeof data.lifecycle_stages] || [];
          if (narratives.length === 0) return null;

          return (
            <div key={stage.key} className="glass rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-3">
                <div className={`w-3 h-3 rounded-full ${stage.color}`}></div>
                <h3 className="text-sm font-semibold text-gray-300">{stage.label}</h3>
              </div>

              <div className="space-y-2">
                {narratives.slice(0, 3).map((item: any) => (
                  <motion.div
                    key={item.narrative}
                    className={`p-2 rounded border ${
                      selectedNarrative === item.narrative
                        ? 'border-primary-500 bg-primary-500/20'
                        : 'border-dark-400 bg-dark-300/30'
                    } cursor-pointer hover:bg-dark-300/50 transition-colors`}
                    whileHover={{ x: 5 }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{item.narrative}</span>
                      <span className="text-xs text-primary-400">
                        {(item.momentum_score * 100).toFixed(0)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-gray-400">
                        Sentiment: {(item.sentiment * 100).toFixed(0)}%
                      </span>
                      <span className={`text-xs ${
                        item.price_change_24h > 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {item.price_change_24h > 0 ? '+' : ''}{(item.price_change_24h * 100).toFixed(1)}%
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Rotation Opportunities */}
      {data.rotation_opportunities && (
        <div className="glass rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Rotation Opportunities</h3>

          <div className="grid grid-cols-3 gap-3 text-xs">
            {Object.entries(data.rotation_opportunities).map(([transition, narratives]) => {
              if (!narratives || (narratives as any[]).length === 0) return null;

              const [from, to] = transition.split('_to_');
              return (
                <div key={transition} className="space-y-1">
                  <div className="text-gray-400 capitalize">
                    {from.replace('_', ' ')} → {to.replace('_', ' ')}
                  </div>
                  {(narratives as any[]).map((item: any) => (
                    <div
                      key={item.narrative}
                      className="p-1 rounded bg-dark-300/50 border border-dark-400"
                    >
                      {item.narrative}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}