# NarrativeFlow - Crypto Narrative Rotation Tracker

**Phases 1-6 Complete: Data Collection, Classification, Divergence Detection, AI Analysis, Dashboard & Telegram Bot**

NarrativeFlow is a tool that detects which crypto narratives are gaining momentum BEFORE prices move, by cross-referencing social sentiment with on-chain data.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              DATA COLLECTION LAYER               │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Social   │ │ On-Chain │ │ Market Data      │ │
│  │          │ │          │ │                  │ │
│  │ CryptoPanic │ DeFiLlama│ │ CoinGecko       │ │
│  │ Reddit   │ │          │ │ Binance         │ │
│  │ RSS News │ │          │ │                  │ │
│  └────┬─────┘ └────┬─────┘ └───────┬──────────┘ │
│       │            │               │             │
└───────┼────────────┼───────────────┼─────────────┘
        │            │               │
        ▼            ▼               ▼
┌─────────────────────────────────────────────────┐
│              SQLITE DATABASE                     │
│                                                  │
│  • Raw social data with sentiment                │
│  • Market prices, volumes, funding rates         │
│  • On-chain TVL and protocol metrics            │
│  • Narrative classification tags                 │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│              FASTAPI ENDPOINTS                   │
│                                                  │
│  GET /social/recent - Recent social mentions     │
│  GET /market/prices - Token prices & metrics     │
│  GET /onchain/tvl - Protocol TVL data           │
│  GET /narratives/stats - Aggregate stats        │
│  GET /search - Search across all data           │
└─────────────────────────────────────────────────┘
```

## Data Sources

### Social Sentiment
- **CryptoPanic API** - Crypto news aggregator with sentiment tags (bullish/bearish), community voting
- **Reddit (PRAW)** - Monitors r/cryptocurrency, r/solana, r/defi, r/altcoin, r/ethtrader
- **RSS Feeds** - The Block, CoinDesk, Decrypt for news articles

### On-Chain Data
- **DeFiLlama API** - TVL by protocol/chain, yields, fees (free, no key required)
- **CoinGecko API** - Categories endpoint gives narrative baskets, prices, volumes

### Market Data
- **Binance API** - Funding rates, open interest, prices for top 50 tokens

## Narrative Taxonomy

The system classifies all data into these narrative categories:
- **AI** - Artificial Intelligence, ML, Agents
- **RWA** - Real World Assets, Tokenization
- **DePIN** - Decentralized Physical Infrastructure
- **Memecoin** - Meme tokens and culture coins
- **L1/L2** - Layer 1 and Layer 2 blockchains
- **NFT** - Non-Fungible Tokens
- **DeFi** - Decentralized Finance
- **Gaming** - GameFi and Metaverse
- **Privacy** - Privacy coins and protocols
- **Derivatives** - Perpetuals, Options, Leverage
- **Social** - Social tokens and platforms
- **Infrastructure** - Oracles, Bridges, Interoperability

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/narrative-flow.git
cd narrative-flow
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys (optional)
```

3. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Local Development

1. Install Python 3.12+

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
python main.py
```

## API Usage

### Check System Health
```bash
curl http://localhost:8000/health
```

### Get Recent Social Data
```bash
# All social data from last 24 hours
curl http://localhost:8000/social/recent

# Filter by source
curl http://localhost:8000/social/recent?source=Reddit

# Filter by narrative
curl http://localhost:8000/social/recent?narrative=AI

# Filter by sentiment
curl http://localhost:8000/social/recent?sentiment=bullish
```

### Get Market Prices
```bash
# All market data
curl http://localhost:8000/market/prices

# Filter by symbol
curl http://localhost:8000/market/prices?symbol=SOL

# Filter by narrative
curl http://localhost:8000/market/prices?narrative=L1/L2
```

### Get On-Chain TVL Data
```bash
# All TVL data
curl http://localhost:8000/onchain/tvl

# Filter by protocol
curl http://localhost:8000/onchain/tvl?protocol=Aave

# Filter by narrative
curl http://localhost:8000/onchain/tvl?narrative=DeFi
```

### Get Narrative Statistics
```bash
# Aggregate stats for all narratives (24h)
curl http://localhost:8000/narratives/stats

# Stats for last 7 days
curl http://localhost:8000/narratives/stats?hours=168
```

### Search Across All Data
```bash
# Search for specific terms
curl "http://localhost:8000/search?q=artificial+intelligence"
```

## Data Collection Schedule

The system polls each data source on a configurable schedule:

| Source | Default Interval | Description |
|--------|-----------------|-------------|
| CryptoPanic | 5 minutes | Crypto news aggregator |
| Reddit | 10 minutes | Subreddit posts |
| RSS Feeds | 15 minutes | News articles |
| DeFiLlama | 30 minutes | TVL and protocol data |
| CoinGecko | 10 minutes | Market data and categories |
| Binance | 1 minute | Prices, funding rates, OI |

## Configuration

All configuration is done through environment variables or the `.env` file:

```env
# Collection Intervals (seconds)
CRYPTOPANIC_INTERVAL=300      # 5 minutes
REDDIT_INTERVAL=600           # 10 minutes
RSS_INTERVAL=900              # 15 minutes
DEFI_LLAMA_INTERVAL=1800      # 30 minutes
COINGECKO_INTERVAL=600        # 10 minutes
BINANCE_INTERVAL=60           # 1 minute

# Optional API Keys
CRYPTOPANIC_API_KEY=          # Optional for free tier
REDDIT_CLIENT_ID=             # Optional, uses read-only without
REDDIT_CLIENT_SECRET=         # Optional
COINGECKO_API_KEY=            # Optional for free tier
```

## Database Schema

The SQLite database stores:

- **raw_data** - All social/news data with sentiment and narrative tags
- **market_data** - Token prices, volumes, funding rates
- **onchain_data** - TVL, active addresses, protocol metrics
- **data_sources** - Source configuration and status
- **narrative_metrics** - Aggregated metrics per narrative (Phase 2)

## Telegram Bot

The NarrativeFlow Telegram bot provides real-time alerts and on-demand market intelligence directly to your Telegram.

### Features

- 🚨 **Real-time Alerts**
  - Divergence signals (early entry, exit, accumulation)
  - Narrative lifecycle transitions
  - Major momentum shifts
  - Rate limiting to prevent spam

- 📱 **Bot Commands**
  - `/narrative <name>` - Get detailed status of a specific narrative
  - `/divergence` - Show current divergence signals
  - `/briefing` - Get AI-generated market briefing
  - `/top` - Show top narratives by momentum
  - `/lifecycle` - View all narratives by lifecycle stage

- ⏰ **Daily Briefings**
  - Automated morning market analysis
  - AI-powered insights on narrative rotations
  - Key signals and opportunities

### Setup

1. **Create a Telegram Bot**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Save the bot token

2. **Get Your Chat ID**
   - Message @userinfobot on Telegram
   - Save your chat ID

3. **Configure Environment**
   ```bash
   # Add to .env file
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

4. **Start the Bot**
   ```bash
   python -m narrative_flow.telegram.main
   ```

### Alert Types

- **Info** ℹ️ - General market updates
- **Warning** ⚠️ - Important signals requiring attention
- **Critical** 🚨 - High-confidence opportunities or risks

## Project Structure

```
narrative-flow/
├── narrative_flow/
│   ├── collectors/       # Data collection modules
│   │   ├── base.py      # Base collector class
│   │   ├── cryptopanic.py
│   │   ├── reddit.py
│   │   ├── rss.py
│   │   ├── defi_llama.py
│   │   ├── coingecko.py
│   │   └── binance.py
│   ├── models/          # Database models
│   │   ├── database.py  # SQLAlchemy models
│   │   └── db_manager.py
│   ├── api/            # FastAPI endpoints
│   │   └── main.py
│   ├── telegram/       # Telegram bot
│   │   ├── bot.py      # Bot implementation
│   │   ├── alerts.py   # Alert management
│   │   ├── websocket_integration.py
│   │   └── main.py     # Bot runner
│   ├── config/         # Configuration
│   │   └── settings.py
│   └── scheduler.py    # Data collection scheduler
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker container definition
├── docker-compose.yml # Docker Compose configuration
└── README.md         # This file
```

## Next Phases

**Phase 2: Narrative Classification + Sentiment**
- AI-powered narrative classification
- Advanced sentiment analysis
- Mention velocity calculation
- Influencer weighting

**Phase 3: Divergence Detection Engine**
- Narrative momentum scoring
- Price divergence signals
- Lifecycle stage detection
- Backtesting framework

**Phase 4: AI Analysis Layer**
- Claude/GPT integration for briefings
- Catalyst identification
- Natural language market analysis

**Phase 5: Frontend Dashboard** ✅
- Next.js dashboard
- Real-time narrative heatmap
- Divergence alerts
- Historical rotation charts

**Phase 6: Telegram Bot + Alerts** ✅
- Real-time alerts via Telegram
- Bot commands for narrative queries
- Rate-limited notifications
- Daily AI-generated briefings

## License

MIT

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.