# NarrativeFlow API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication for public endpoints. Future versions will implement API key authentication.

## Rate Limiting
- Default: 100 requests per minute per IP
- Burst: 10 concurrent requests

## Endpoints

### Health & Status

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-26T12:00:00Z",
  "service": "NarrativeFlow API",
  "version": "1.0.0"
}
```

#### GET /metrics
Get system performance metrics.

**Response:**
```json
{
  "success": true,
  "metrics": {
    "data_throughput_per_second": 1247.3,
    "classification_speed_ms": 67.2,
    "api_response_time_ms": 124.5,
    "uptime_hours": 48.2
  }
}
```

### Narratives

#### GET /narratives/current
Get current momentum scores for all narratives.

**Query Parameters:**
- `hours` (int, optional): Time window in hours (default: 24)

**Response:**
```json
{
  "success": true,
  "timestamp": "2025-02-26T12:00:00Z",
  "narratives": [
    {
      "name": "AI",
      "social_momentum": 0.85,
      "onchain_momentum": 0.72,
      "price_momentum": 0.45,
      "overall_score": 0.67,
      "lifecycle_stage": "momentum",
      "trend": "rising",
      "top_tokens": ["TAO", "FET", "RNDR"]
    }
  ]
}
```

#### GET /narratives/stats
Get aggregate statistics for narratives.

**Query Parameters:**
- `hours` (int, optional): Time window (default: 24)
- `narrative` (string, optional): Filter by specific narrative

**Response:**
```json
{
  "success": true,
  "stats": {
    "AI": {
      "mentions_total": 12453,
      "mentions_per_hour": 518.9,
      "sentiment_avg": 0.72,
      "tvl_change_pct": 15.3,
      "price_change_24h": 8.7
    }
  }
}
```

#### GET /narratives/{narrative}/history
Get historical data for a specific narrative.

**Path Parameters:**
- `narrative` (string): Narrative name (AI, RWA, DePIN, etc.)

**Query Parameters:**
- `days` (int, optional): Days of history (default: 7, max: 30)

**Response:**
```json
{
  "success": true,
  "narrative": "AI",
  "history": [
    {
      "timestamp": "2025-02-26T00:00:00Z",
      "social_momentum": 0.65,
      "onchain_momentum": 0.58,
      "price_momentum": 0.42,
      "lifecycle_stage": "accumulation"
    }
  ]
}
```

### Divergences

#### GET /divergences/active
Get currently active divergence signals.

**Query Parameters:**
- `min_strength` (float, optional): Minimum signal strength (0-1, default: 0.6)

**Response:**
```json
{
  "success": true,
  "divergences": [
    {
      "id": "div_123",
      "narrative": "DePIN",
      "type": "early_entry",
      "strength": 0.78,
      "detected_at": "2025-02-26T10:30:00Z",
      "metrics": {
        "social_momentum": 0.82,
        "onchain_momentum": 0.75,
        "price_momentum": 0.25
      },
      "recommended_action": "Consider entry - strong divergence detected",
      "top_tokens": ["HNT", "MOBILE", "RNDR"]
    }
  ]
}
```

#### GET /divergences/history
Get historical divergence signals.

**Query Parameters:**
- `days` (int, optional): Days of history (default: 7)
- `type` (string, optional): Signal type filter (early_entry, late_exit, accumulation)

**Response:**
```json
{
  "success": true,
  "total": 45,
  "signals": [
    {
      "id": "div_098",
      "narrative": "AI",
      "type": "late_exit",
      "strength": 0.71,
      "detected_at": "2025-02-25T14:20:00Z",
      "outcome": "successful",
      "price_move_after_signal": 12.3
    }
  ]
}
```

### Analysis

#### GET /analysis/daily
Get AI-generated daily market briefing.

**Response:**
```json
{
  "success": true,
  "briefing": {
    "generated_at": "2025-02-26T06:00:00Z",
    "summary": "AI narrative showing strong momentum...",
    "top_narratives": ["AI", "RWA", "DePIN"],
    "signals": [
      {
        "narrative": "AI",
        "action": "early_entry",
        "confidence": 0.82,
        "reasoning": "Social buzz up 340% but price flat"
      }
    ],
    "catalysts": [
      "OpenAI announces GPT-5",
      "BlackRock launches tokenized fund"
    ],
    "risks": [
      "Regulatory uncertainty in EU",
      "Potential market correction"
    ]
  }
}
```

#### POST /analysis/query
Query the AI for specific market analysis.

**Request Body:**
```json
{
  "query": "What's driving the AI narrative today?",
  "include_data": true
}
```

**Response:**
```json
{
  "success": true,
  "analysis": "The AI narrative is being driven by...",
  "supporting_data": {
    "social_mentions": 2341,
    "top_influencers": ["@ai_whale", "@crypto_ai"],
    "key_topics": ["autonomous agents", "AI infrastructure"]
  }
}
```

### Alerts

#### GET /alerts/active
Get active alert configurations.

**Response:**
```json
{
  "success": true,
  "alerts": [
    {
      "id": "alert_001",
      "type": "divergence",
      "narrative": "all",
      "threshold": 0.7,
      "channel": "telegram",
      "enabled": true
    }
  ]
}
```

#### POST /alerts/subscribe
Subscribe to specific alerts.

**Request Body:**
```json
{
  "type": "divergence",
  "narratives": ["AI", "RWA"],
  "min_strength": 0.6,
  "channels": ["telegram", "webhook"],
  "webhook_url": "https://your-webhook.com/alerts"
}
```

**Response:**
```json
{
  "success": true,
  "alert_id": "alert_002",
  "message": "Alert subscription created"
}
```

### Backtest

#### GET /backtest/results
Get comprehensive backtest results.

**Response:**
```json
{
  "success": true,
  "backtest_period": "2024-01-15 to 2025-02-26",
  "thesis": "Follow divergence signals for alpha",
  "results": {
    "total_return_pct": 62.89,
    "win_rate": 0.732,
    "sharpe_ratio": 1.84,
    "max_drawdown_pct": -12.3,
    "total_trades": 127,
    "performance_by_narrative": {
      "AI": {
        "trades": 23,
        "win_rate": 0.78,
        "total_return": 142.3
      }
    }
  }
}
```

#### GET /backtest/trades
Get historical trades from backtest.

**Query Parameters:**
- `narrative` (string, optional): Filter by narrative
- `signal_type` (string, optional): Filter by signal type
- `limit` (int, optional): Max results (default: 100)

**Response:**
```json
{
  "success": true,
  "trades": [
    {
      "entry_time": "2024-03-15T10:00:00Z",
      "exit_time": "2024-03-18T14:00:00Z",
      "narrative": "AI",
      "signal_type": "early_entry",
      "pnl_pct": 23.5,
      "signal_strength": 0.82
    }
  ]
}
```

### Market Data

#### GET /market/prices
Get current market prices and metrics.

**Query Parameters:**
- `symbols` (string, optional): Comma-separated token symbols
- `narrative` (string, optional): Filter by narrative

**Response:**
```json
{
  "success": true,
  "prices": [
    {
      "symbol": "TAO",
      "price": 245.67,
      "change_24h": 8.3,
      "volume_24h": 45678900,
      "market_cap": 1234567890,
      "narrative": "AI",
      "funding_rate": 0.012
    }
  ]
}
```

### Social Data

#### GET /social/recent
Get recent social mentions.

**Query Parameters:**
- `source` (string, optional): Filter by source (Twitter, Reddit, etc.)
- `narrative` (string, optional): Filter by narrative
- `sentiment` (string, optional): Filter by sentiment (bullish, bearish, neutral)
- `hours` (int, optional): Time window (default: 24)

**Response:**
```json
{
  "success": true,
  "mentions": [
    {
      "id": "mention_123",
      "source": "Twitter",
      "author": "@crypto_whale",
      "content": "AI narrative is just getting started...",
      "sentiment": "bullish",
      "narratives": ["AI"],
      "engagement": 1234,
      "timestamp": "2025-02-26T11:30:00Z"
    }
  ]
}
```

## WebSocket Endpoints

### WS /ws/signals
Real-time divergence signals stream.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/signals');

ws.onmessage = (event) => {
  const signal = JSON.parse(event.data);
  console.log('New signal:', signal);
};
```

**Message Format:**
```json
{
  "type": "divergence",
  "narrative": "AI",
  "signal_type": "early_entry",
  "strength": 0.78,
  "timestamp": "2025-02-26T12:00:00Z"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "status_code": 400,
  "timestamp": "2025-02-26T12:00:00Z"
}
```

### Common Status Codes
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Data Types

### Narratives
- `AI` - Artificial Intelligence
- `RWA` - Real World Assets
- `DePIN` - Decentralized Physical Infrastructure
- `Memecoins` - Meme tokens
- `L2` - Layer 2 solutions
- `Gaming` - GameFi and Metaverse
- `DeFi` - Decentralized Finance
- `NFT` - Non-Fungible Tokens

### Signal Types
- `early_entry` - High social/onchain, low price
- `late_exit` - High price, declining momentum
- `accumulation` - Smart money accumulating

### Lifecycle Stages
- `whisper` - 0-15% of cycle
- `accumulation` - 15-30% of cycle
- `momentum` - 30-60% of cycle
- `fomo` - 60-85% of cycle
- `distribution` - 85-95% of cycle
- `decline` - 95-100% of cycle

## Examples

### Python
```python
import requests

# Get current narratives
response = requests.get('http://localhost:8000/narratives/current')
data = response.json()

for narrative in data['narratives']:
    print(f"{narrative['name']}: {narrative['overall_score']}")
```

### JavaScript
```javascript
// Get active divergences
fetch('http://localhost:8000/divergences/active?min_strength=0.7')
  .then(res => res.json())
  .then(data => {
    data.divergences.forEach(signal => {
      console.log(`${signal.narrative}: ${signal.type} (${signal.strength})`);
    });
  });
```

### cURL
```bash
# Get daily briefing
curl -X GET "http://localhost:8000/analysis/daily" \
  -H "Accept: application/json"

# Subscribe to alerts
curl -X POST "http://localhost:8000/alerts/subscribe" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "divergence",
    "narratives": ["AI", "RWA"],
    "min_strength": 0.6
  }'
```

## Changelog

### v1.0.0 (2025-02-26)
- Initial release
- Core endpoints for narratives, divergences, analysis
- Backtest results and historical data
- WebSocket support for real-time signals
- Telegram bot integration