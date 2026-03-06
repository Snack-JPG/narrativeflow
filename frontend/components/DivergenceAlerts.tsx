'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import wsClient, { DivergenceAlert } from '@/lib/websocket';
import { divergenceAPI } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

export default function DivergenceAlerts() {
  const [alerts, setAlerts] = useState<DivergenceAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load initial alerts
    loadInitialAlerts();

    // Subscribe to WebSocket alerts
    const handlers = [
      wsClient.on('divergence_alert', (alert: DivergenceAlert) => {
        setAlerts(prev => [alert, ...prev].slice(0, 50)); // Keep last 50
      }),
      wsClient.on('lifecycle_change', (alert: DivergenceAlert) => {
        setAlerts(prev => [alert, ...prev].slice(0, 50));
      }),
      wsClient.on('whale_move', (alert: DivergenceAlert) => {
        setAlerts(prev => [alert, ...prev].slice(0, 50));
      }),
      wsClient.on('catalyst_event', (alert: DivergenceAlert) => {
        setAlerts(prev => [alert, ...prev].slice(0, 50));
      }),
    ];

    return () => {
      handlers.forEach(cleanup => cleanup());
    };
  }, []);

  const loadInitialAlerts = async () => {
    try {
      const data = await divergenceAPI.getCurrent();

      // Convert API signals to alerts
      const initialAlerts: DivergenceAlert[] = data.current_signals.map((signal: any) => ({
        type: 'divergence_alert',
        narrative: signal.narrative,
        signal: signal.signal,
        lifecycle: signal.lifecycle,
        confidence: signal.confidence,
        message: getAlertMessage(signal),
        timestamp: signal.timestamp,
        metadata: signal
      }));

      setAlerts(initialAlerts);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load alerts:', error);
      setLoading(false);
    }
  };

  const getAlertMessage = (signal: any) => {
    const confidencePercent = (signal.confidence * 100).toFixed(0);

    switch (signal.signal) {
      case 'early_entry':
        return `Early entry opportunity detected in ${signal.narrative} (${confidencePercent}% confidence)`;
      case 'accumulation':
        return `Smart money accumulating ${signal.narrative} while price is flat`;
      case 'late_exit':
        return `Exit signal for ${signal.narrative} - price peaked, momentum declining`;
      case 'dead':
        return `${signal.narrative} narrative showing no activity - avoid`;
      default:
        return `${signal.narrative} signal: ${signal.signal}`;
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'divergence_alert':
        return '📊';
      case 'lifecycle_change':
        return '🔄';
      case 'whale_move':
        return '🐋';
      case 'catalyst_event':
        return '⚡';
      default:
        return '📢';
    }
  };

  const getAlertColor = (alert: DivergenceAlert) => {
    if (alert.signal === 'early_entry' || alert.signal === 'accumulation') {
      return 'border-green-500/50 bg-green-500/10';
    } else if (alert.signal === 'late_exit' || alert.signal === 'dead') {
      return 'border-red-500/50 bg-red-500/10';
    } else if (alert.type === 'whale_move') {
      return 'border-blue-500/50 bg-blue-500/10';
    } else if (alert.type === 'catalyst_event') {
      return 'border-yellow-500/50 bg-yellow-500/10';
    }
    return 'border-gray-500/50 bg-gray-500/10';
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 bg-dark-300/20 rounded-lg loading-pulse"></div>
        ))}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No alerts yet</p>
        <p className="text-sm mt-2">Monitoring narratives...</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <AnimatePresence mode="popLayout">
        {alerts.map((alert, index) => (
          <motion.div
            key={`${alert.timestamp}-${index}`}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -100 }}
            transition={{ duration: 0.3 }}
            className={`p-3 rounded-lg border ${getAlertColor(alert)} glass-hover cursor-pointer`}
          >
            <div className="flex items-start space-x-2">
              <span className="text-xl">{getAlertIcon(alert.type)}</span>
              <div className="flex-1">
                <p className="text-sm text-gray-200">{alert.message}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                  </span>
                  {alert.confidence && (
                    <span className="text-xs text-primary-400">
                      {(alert.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Additional metadata display */}
            {alert.metadata && (
              <div className="mt-2 pt-2 border-t border-dark-400/30 text-xs text-gray-400 grid grid-cols-2 gap-1">
                {alert.metadata.price_change_24h && (
                  <div>Price 24h: {(alert.metadata.price_change_24h * 100).toFixed(1)}%</div>
                )}
                {alert.metadata.social_velocity && (
                  <div>Velocity: {alert.metadata.social_velocity.toFixed(0)}/hr</div>
                )}
                {alert.metadata.tvl && (
                  <div>TVL: ${(alert.metadata.tvl / 1000000).toFixed(1)}M</div>
                )}
                {alert.lifecycle && (
                  <div>Stage: {alert.lifecycle}</div>
                )}
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}